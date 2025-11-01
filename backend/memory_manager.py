"""
RAG记忆管理模块
实现向量存储、检索和上下文优化功能
支持FAISS向量索引、向量缓存和持久化
"""
import json
import os
import hashlib
import pickle
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import numpy as np
from sentence_transformers import SentenceTransformer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("FAISS未安装，将使用线性搜索")


class MemoryManager:
    """RAG记忆管理器 - 支持向量缓存、FAISS索引和持久化"""
    
    def __init__(self, 
                 model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                 storage_path: str = "conversation_memory.json",
                 max_recent_messages: int = 16,
                 retrieval_top_k: int = 10,
                 similarity_threshold: float = 0.3):
        """
        初始化记忆管理器
        
        Args:
            model_name: Embedding模型名称（使用多语言模型支持中文）
            storage_path: 记忆存储文件路径
            max_recent_messages: 保留的最近消息数量（16条 = 8个对话来回）
            retrieval_top_k: 检索返回的最相关消息数量
            similarity_threshold: 相似度阈值，低于此值不返回
        """
        # 如果路径是相对路径，转换为基于当前文件的绝对路径
        if not os.path.isabs(storage_path):
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.storage_path = os.path.join(current_dir, storage_path)
        else:
            self.storage_path = storage_path
        
        # 向量存储路径
        self.vectors_path = self.storage_path.replace('.json', '_vectors.pkl')
        self.cache_path = self.storage_path.replace('.json', '_cache.pkl')
        
        logger.info(f"记忆存储路径: {self.storage_path}")
        logger.info(f"向量存储路径: {self.vectors_path}")
        logger.info(f"缓存存储路径: {self.cache_path}")
        
        self.max_recent_messages = max_recent_messages
        self.retrieval_top_k = retrieval_top_k
        self.similarity_threshold = similarity_threshold
        
        # 向量缓存：{content_hash: vector}
        self.vector_cache = {}
        
        # 向量索引：{conversation_id: faiss_index}
        self.faiss_indices = {}
        # 消息索引映射：{conversation_id: [message_index_in_faiss -> message_dict]}
        self.message_index_maps = {}
        
        # 加载embedding模型（在初始化时加载）
        logger.info(f"正在加载embedding模型: {model_name}")
        try:
            self.embedder = SentenceTransformer(model_name)
            self.embedding_dim = self.embedder.get_sentence_embedding_dimension()
            logger.info(f"Embedding模型加载成功，向量维度: {self.embedding_dim}")
        except Exception as e:
            logger.error(f"加载embedding模型失败: {e}")
            raise
        
        # 记忆存储：{conversation_id: {messages: [...], metadata: {...}}}
        self.memory = {}
        self._load_memory()
        self._load_vectors()
        self._load_cache()
    
    def _get_content_hash(self, content: str) -> str:
        """生成消息内容的hash"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _load_cache(self):
        """加载向量缓存"""
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'rb') as f:
                    self.vector_cache = pickle.load(f)
                logger.info(f"已加载向量缓存: {len(self.vector_cache)} 个向量")
            except Exception as e:
                logger.warning(f"加载向量缓存失败: {e}，将重新构建")
                self.vector_cache = {}
        else:
            self.vector_cache = {}
    
    def _save_cache(self):
        """保存向量缓存"""
        try:
            with open(self.cache_path, 'wb') as f:
                pickle.dump(self.vector_cache, f)
            logger.debug(f"向量缓存已保存: {len(self.vector_cache)} 个向量")
        except Exception as e:
            logger.warning(f"保存向量缓存失败: {e}")
    
    def _get_vector(self, content: str) -> np.ndarray:
        """获取内容的向量（使用缓存）"""
        if not content or len(content.strip()) < 3:
            return None
        
        content_hash = self._get_content_hash(content)
        
        # 检查缓存
        if content_hash in self.vector_cache:
            return self.vector_cache[content_hash]
        
        # 计算向量
        try:
            vector = self.embedder.encode(content, normalize_embeddings=True)
            self.vector_cache[content_hash] = vector
            
            # 定期保存缓存（每100次）
            if len(self.vector_cache) % 100 == 0:
                self._save_cache()
            
            return vector
        except Exception as e:
            logger.error(f"生成向量失败: {e}")
            return None
    
    def _load_memory(self):
        """从文件加载记忆"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.memory = {
                        conv_id: {
                            'messages': conv_data['messages'],
                            'metadata': conv_data.get('metadata', {})
                        }
                        for conv_id, conv_data in data.items()
                    }
                logger.info(f"已加载 {len(self.memory)} 个对话的记忆")
            except Exception as e:
                logger.error(f"加载记忆失败: {e}")
                self.memory = {}
        else:
            self.memory = {}
    
    def _load_vectors(self):
        """加载向量索引和持久化的向量"""
        if not FAISS_AVAILABLE:
            logger.warning("FAISS未安装，跳过向量索引加载")
            return
        
        if os.path.exists(self.vectors_path):
            try:
                with open(self.vectors_path, 'rb') as f:
                    data = pickle.load(f)
                    self.faiss_indices = data.get('faiss_indices', {})
                    self.message_index_maps = data.get('message_index_maps', {})
                    
                    # 重建FAISS索引
                    for conv_id, index_data in self.faiss_indices.items():
                        if isinstance(index_data, dict):
                            # 重建FAISS索引
                            vectors = index_data.get('vectors', np.array([]))
                            if len(vectors) > 0:
                                dimension = vectors.shape[1]
                                index = faiss.IndexFlatIP(dimension)  # Inner Product (cosine similarity)
                                index.add(vectors.astype('float32'))
                                self.faiss_indices[conv_id] = index
                                logger.info(f"已重建对话 {conv_id} 的FAISS索引: {len(vectors)} 个向量")
                    
                logger.info(f"已加载向量索引: {len(self.faiss_indices)} 个对话")
            except Exception as e:
                logger.warning(f"加载向量索引失败: {e}，将重新构建")
                self.faiss_indices = {}
                self.message_index_maps = {}
        else:
            self.faiss_indices = {}
            self.message_index_maps = {}
    
    def _save_vectors(self):
        """保存向量索引"""
        if not FAISS_AVAILABLE:
            return
        
        try:
            # 保存FAISS索引数据（需要提取向量）
            save_data = {}
            for conv_id, index in self.faiss_indices.items():
                if isinstance(index, faiss.Index):
                    # 从FAISS索引中提取向量（用于持久化）
                    num_vectors = index.ntotal
                    if num_vectors > 0:
                        vectors = index.reconstruct_n(0, num_vectors)
                        save_data[conv_id] = {
                            'vectors': vectors,
                            'dimension': index.d
                        }
            
            data = {
                'faiss_indices': save_data,
                'message_index_maps': self.message_index_maps
            }
            
            with open(self.vectors_path, 'wb') as f:
                pickle.dump(data, f)
            logger.info(f"向量索引已保存: {len(self.faiss_indices)} 个对话")
        except Exception as e:
            logger.warning(f"保存向量索引失败: {e}")
    
    def _build_faiss_index(self, conversation_id: str):
        """为对话构建FAISS索引"""
        if not FAISS_AVAILABLE:
            return
        
        if conversation_id not in self.memory:
            return
        
        messages = self.memory[conversation_id]['messages']
        conversation_messages = [msg for msg in messages if msg.get('role') != 'system']
        
        if not conversation_messages:
            return
        
        # 生成向量
        vectors = []
        message_map = []
        
        for msg in conversation_messages:
            content = msg.get('content', '')
            if not content or len(content.strip()) < 3:
                continue
            
            vector = self._get_vector(content)
            if vector is not None:
                vectors.append(vector)
                message_map.append(msg)
        
        if not vectors:
            return
        
        # 创建FAISS索引
        vectors_array = np.array(vectors).astype('float32')
        dimension = vectors_array.shape[1]
        
        # 使用Inner Product（内积）索引，因为向量已归一化，内积=余弦相似度
        index = faiss.IndexFlatIP(dimension)
        index.add(vectors_array)
        
        self.faiss_indices[conversation_id] = index
        self.message_index_maps[conversation_id] = message_map
        
        logger.info(f"已为对话 {conversation_id} 构建FAISS索引: {len(vectors)} 个向量")
    
    def _save_memory(self):
        """保存记忆到文件（只保存消息和元数据，向量单独保存）"""
        try:
            data = {
                conv_id: {
                    'messages': conv_data['messages'],
                    'metadata': conv_data.get('metadata', {})
                }
                for conv_id, conv_data in self.memory.items()
            }
            logger.info(f"保存记忆到文件: {self.storage_path}, 对话数量: {len(data)}")
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"记忆保存成功: {len(data)} 个对话")
            
            # 保存向量索引
            self._save_vectors()
            # 保存缓存
            self._save_cache()
        except Exception as e:
            logger.error(f"保存记忆失败: {e}", exc_info=True)
            import traceback
            logger.error(traceback.format_exc())
    
    def _get_conversation_id(self, conversation_history: List[Dict]) -> str:
        """从对话历史生成或获取对话ID"""
        for msg in conversation_history:
            if 'conversation_id' in msg:
                return msg['conversation_id']
        
        if conversation_history:
            first_msg = conversation_history[0]
            content = first_msg.get('content', '')
            return hashlib.md5(content.encode()).hexdigest()[:16]
        
        return "default"
    
    def _get_sliding_window(self, messages: List[Dict], max_messages: int) -> List[Dict]:
        """
        获取滑动窗口内的消息（简化版本）
        
        核心逻辑：
        1. 从后往前取 max_messages-1 条消息（为当前消息留一个位置）
        2. 确保第一个消息是user（如果第一个是assistant，往前找user）
        3. 不做复杂的配对检查，直接返回
        
        Args:
            messages: 非系统消息列表（按时间顺序）
            max_messages: 最大消息数量（16 = 8个对话来回）
        
        Returns:
            滑动窗口内的消息列表，确保第一个是user
        """
        if not messages:
            return []
        
        target_count = max_messages - 1  # 15条历史消息（为当前user消息留一个位置）
        
        # 如果消息数量不足target_count，直接返回所有消息
        if len(messages) <= target_count:
            return messages
        
        # 直接取最后 target_count 条消息
        window = messages[-target_count:]
        
        # 关键修复：确保第一个消息是user
        # 如果第一个是assistant，说明前面的user消息被截断了，需要往前找
        if window and window[0].get('role') != 'user':
            # 在原始消息中往前找user消息
            window_start_idx = len(messages) - target_count
            for i in range(window_start_idx - 1, -1, -1):
                if messages[i].get('role') == 'user':
                    # 从这个user开始，取到末尾
                    window = messages[i:]
                    # 如果超过target_count，截断到target_count
                    if len(window) > target_count:
                        window = window[:target_count]
                    break
            else:
                # 如果没找到user，返回空（这种情况不应该发生）
                logger.warning("警告：滑动窗口中没有找到user消息，返回空列表")
                return []
        
        logger.info(f"滑动窗口: 选择了 {len(window)} 条历史消息")
        logger.info(f"  - 第一条role: {window[0].get('role') if window else 'N/A'}")
        logger.info(f"  - 最后一条role: {window[-1].get('role') if window else 'N/A'}")
        
        return window
    
    def add_messages(self, conversation_id: str, messages: List[Dict]):
        """添加消息到记忆"""
        logger.info(f"添加消息到对话 {conversation_id}, 消息数量: {len(messages)}")
        
        if conversation_id not in self.memory:
            self.memory[conversation_id] = {
                'messages': [],
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
            }
            logger.info(f"创建新对话: {conversation_id}")
        
        existing_ids = {msg.get('id') for msg in self.memory[conversation_id]['messages'] if 'id' in msg}
        added_count = 0
        for msg in messages:
            msg_id = msg.get('id')
            if msg_id and msg_id in existing_ids:
                logger.debug(f"跳过已存在的消息: {msg_id}")
                continue
            
            if not msg_id:
                msg['id'] = f"{conversation_id}_{len(self.memory[conversation_id]['messages'])}"
            
            self.memory[conversation_id]['messages'].append(msg)
            added_count += 1
        
        logger.info(f"成功添加 {added_count} 条消息到对话 {conversation_id}")
        
        self.memory[conversation_id]['metadata']['updated_at'] = datetime.now().isoformat()
        self.memory[conversation_id]['metadata']['message_count'] = len(self.memory[conversation_id]['messages'])
        
        # 重建FAISS索引
        self._build_faiss_index(conversation_id)
        
        self._save_memory()
    
    def _calculate_time_decay(self, timestamp: str, current_time: datetime) -> float:
        """计算时间衰减因子（最近的消息权重更高）"""
        try:
            msg_time = datetime.fromisoformat(timestamp)
            hours_diff = (current_time - msg_time).total_seconds() / 3600
            
            if hours_diff <= 24:
                return 1.0
            elif hours_diff <= 168:  # 7天
                return 0.8
            elif hours_diff <= 720:  # 30天
                return 0.5
            else:
                return 0.3
        except Exception:
            return 0.5
    
    def retrieve_relevant_messages(self, 
                                   conversation_id: str, 
                                   query: str,
                                   exclude_recent_count: int = 0,
                                   cross_conversation: bool = True) -> List[Dict]:
        """
        检索与查询相关的消息（使用FAISS索引）
        
        Args:
            conversation_id: 当前对话ID
            query: 查询文本
            exclude_recent_count: 排除最近N条消息（已在滑动窗口中的消息）
            cross_conversation: 是否启用跨对话检索（默认True，检索所有对话）
        
        Returns:
            相关消息列表（按相关性排序）
        """
        if cross_conversation:
            # 跨对话检索：在所有对话中检索
            return self._retrieve_cross_conversation(conversation_id, query, exclude_recent_count)
        else:
            # 单对话检索：只在当前对话中检索
            return self._retrieve_single_conversation(conversation_id, query, exclude_recent_count)
    
    def _retrieve_single_conversation(self,
                                      conversation_id: str,
                                      query: str,
                                      exclude_recent_count: int = 0) -> List[Dict]:
        """在当前对话中检索"""
        if conversation_id not in self.memory:
            return []
        
        messages = self.memory[conversation_id]['messages']
        
        if len(messages) <= exclude_recent_count:
            return []
        
        system_messages = [msg for msg in messages if msg.get('role') == 'system']
        conversation_messages = [
            msg for msg in messages 
            if msg.get('role') != 'system'
        ]
        
        old_messages = conversation_messages[:-exclude_recent_count] if exclude_recent_count > 0 else conversation_messages
        
        if not old_messages:
            return []
        
        # 生成查询向量
        query_vector = self._get_vector(query)
        if query_vector is None:
            return []
        
        query_vector = query_vector.reshape(1, -1).astype('float32')
        current_time = datetime.now()
        
        # 获取当前对话的最近消息（用于排除）
        current_conversation_messages = []
        if conversation_id in self.memory:
            current_conversation_messages = [
                msg for msg in self.memory[conversation_id]['messages']
                if msg.get('role') != 'system'
            ]
        
        # 使用FAISS索引检索
        if FAISS_AVAILABLE and conversation_id in self.faiss_indices:
            try:
                index = self.faiss_indices[conversation_id]
                message_map = self.message_index_maps[conversation_id]
                
                # 确保索引中有向量
                if index.ntotal == 0:
                    logger.debug(f"FAISS索引为空，跳过检索")
                    return []
                
                logger.info(f"使用FAISS检索（单对话）: 索引中有 {index.ntotal} 个向量，查询向量维度: {query_vector.shape[1]}")
                
                # 使用FAISS搜索（返回top-k*2，然后应用时间衰减和阈值过滤）
                k = min(self.retrieval_top_k * 3, index.ntotal)
                similarities, indices = index.search(query_vector, k)
                
                logger.debug(f"FAISS搜索返回 {len(similarities[0])} 个候选结果")
                
                results = []
                for i, (similarity, idx) in enumerate(zip(similarities[0], indices[0])):
                    if idx >= len(message_map):
                        continue
                    
                    msg = message_map[idx]
                    
                    # 检查是否在排除列表中
                    if exclude_recent_count > 0:
                        msg_pos = -1
                        for j, m in enumerate(current_conversation_messages):
                            if m.get('id') == msg.get('id'):
                                msg_pos = j
                                break
                        if msg_pos >= len(current_conversation_messages) - exclude_recent_count:
                            continue
                    
                    # 时间衰减
                    timestamp = msg.get('timestamp', msg.get('created_at', datetime.now().isoformat()))
                    time_decay = self._calculate_time_decay(timestamp, current_time)
                    
                    # 综合得分
                    final_score = float(similarity) * time_decay
                    
                    if final_score >= self.similarity_threshold:
                        results.append({
                            'message': msg,
                            'score': final_score,
                            'similarity': float(similarity),
                            'time_decay': time_decay
                        })
                
                # 按得分排序
                results.sort(key=lambda x: x['score'], reverse=True)
                
                final_count = len(results[:self.retrieval_top_k])
                logger.info(f"FAISS检索完成（单对话）: 找到 {len(results)} 个结果，返回 {final_count} 个（阈值过滤后）")
                
                # 返回top-k
                return [r['message'] for r in results[:self.retrieval_top_k]]
                
            except Exception as e:
                logger.warning(f"FAISS检索失败，回退到线性搜索: {e}", exc_info=True)
        else:
            if not FAISS_AVAILABLE:
                logger.debug("FAISS未安装，使用线性搜索")
            elif conversation_id not in self.faiss_indices:
                logger.debug(f"对话 {conversation_id} 没有FAISS索引，使用线性搜索")
        
        # 回退到线性搜索
        logger.info(f"使用线性搜索检索（历史消息数: {len(old_messages)}）")
        results = []
        for msg in old_messages:
            content = msg.get('content', '')
            if not content or len(content.strip()) < 3:
                continue
            
            msg_vector = self._get_vector(content)
            if msg_vector is None:
                continue
            
            similarity = float(np.dot(query_vector[0], msg_vector))
            timestamp = msg.get('timestamp', msg.get('created_at', datetime.now().isoformat()))
            time_decay = self._calculate_time_decay(timestamp, current_time)
            final_score = similarity * time_decay
            
            if final_score >= self.similarity_threshold:
                results.append({
                    'message': msg,
                    'score': final_score,
                    'similarity': similarity,
                    'time_decay': time_decay
                })
        
        results.sort(key=lambda x: x['score'], reverse=True)
        return [r['message'] for r in results[:self.retrieval_top_k]]
    
    def _retrieve_cross_conversation(self,
                                     conversation_id: str,
                                     query: str,
                                     exclude_recent_count: int = 0) -> List[Dict]:
        """跨对话检索：在所有对话中检索相关消息"""
        # 生成查询向量
        query_vector = self._get_vector(query)
        if query_vector is None:
            return []
        
        query_vector = query_vector.reshape(1, -1).astype('float32')
        current_time = datetime.now()
        
        # 获取当前对话的最近消息（用于排除）
        current_conversation_messages = []
        if conversation_id in self.memory:
            current_conversation_messages = [
                msg for msg in self.memory[conversation_id]['messages']
                if msg.get('role') != 'system'
            ]
        
        all_results = []
        
        # 在所有对话的FAISS索引中搜索
        if FAISS_AVAILABLE:
            for conv_id, index in self.faiss_indices.items():
                if conv_id == conversation_id:
                    # 对于当前对话，排除最近的消息
                    continue
                
                try:
                    message_map = self.message_index_maps.get(conv_id, [])
                    
                    if index.ntotal == 0:
                        continue
                    
                    # 在每个对话的索引中搜索
                    k = min(self.retrieval_top_k * 2, index.ntotal)
                    similarities, indices = index.search(query_vector, k)
                    
                    # 处理搜索结果
                    for similarity, idx in zip(similarities[0], indices[0]):
                        if idx >= len(message_map):
                            continue
                        
                        msg = message_map[idx]
                        msg['_source_conversation'] = conv_id  # 标记来源对话
                        
                        # 时间衰减
                        timestamp = msg.get('timestamp', msg.get('created_at', datetime.now().isoformat()))
                        time_decay = self._calculate_time_decay(timestamp, current_time)
                        
                        # 跨对话的权重稍微降低（乘以0.9），因为跨对话的相关性可能略低
                        cross_conversation_factor = 0.9
                        final_score = float(similarity) * time_decay * cross_conversation_factor
                        
                        if final_score >= self.similarity_threshold:
                            all_results.append({
                                'message': msg,
                                'score': final_score,
                                'similarity': float(similarity),
                                'time_decay': time_decay
                            })
                
                except Exception as e:
                    logger.warning(f"在对话 {conv_id} 中检索失败: {e}")
                    continue
        
        # 如果当前对话有FAISS索引，也在其中搜索（排除最近消息）
        if FAISS_AVAILABLE and conversation_id in self.faiss_indices:
            try:
                index = self.faiss_indices[conversation_id]
                message_map = self.message_index_maps[conversation_id]
                
                if index.ntotal > 0:
                    k = min(self.retrieval_top_k * 3, index.ntotal)
                    similarities, indices = index.search(query_vector, k)
                    
                    for similarity, idx in zip(similarities[0], indices[0]):
                        if idx >= len(message_map):
                            continue
                        
                        msg = message_map[idx]
                        
                        # 检查是否在排除列表中
                        if exclude_recent_count > 0:
                            msg_pos = -1
                            for j, m in enumerate(current_conversation_messages):
                                if m.get('id') == msg.get('id'):
                                    msg_pos = j
                                    break
                            if msg_pos >= len(current_conversation_messages) - exclude_recent_count:
                                continue
                        
                        # 时间衰减
                        timestamp = msg.get('timestamp', msg.get('created_at', datetime.now().isoformat()))
                        time_decay = self._calculate_time_decay(timestamp, current_time)
                        
                        # 当前对话的消息权重更高（不降低）
                        final_score = float(similarity) * time_decay
                        
                        if final_score >= self.similarity_threshold:
                            all_results.append({
                                'message': msg,
                                'score': final_score,
                                'similarity': float(similarity),
                                'time_decay': time_decay
                            })
            
            except Exception as e:
                logger.warning(f"在当前对话 {conversation_id} 中检索失败: {e}")
        
        # 如果FAISS不可用或没有索引，使用线性搜索
        if not FAISS_AVAILABLE or len(self.faiss_indices) == 0:
            logger.info(f"使用线性搜索进行跨对话检索")
            for conv_id, conv_data in self.memory.items():
                messages = conv_data.get('messages', [])
                conversation_messages = [msg for msg in messages if msg.get('role') != 'system']
                
                # 对于当前对话，排除最近的消息
                if conv_id == conversation_id:
                    if len(conversation_messages) <= exclude_recent_count:
                        continue
                    old_messages = conversation_messages[:-exclude_recent_count]
                else:
                    old_messages = conversation_messages
                
                for msg in old_messages:
                    content = msg.get('content', '')
                    if not content or len(content.strip()) < 3:
                        continue
                    
                    msg_vector = self._get_vector(content)
                    if msg_vector is None:
                        continue
                    
                    similarity = float(np.dot(query_vector[0], msg_vector))
                    timestamp = msg.get('timestamp', msg.get('created_at', datetime.now().isoformat()))
                    time_decay = self._calculate_time_decay(timestamp, current_time)
                    
                    # 跨对话的权重稍微降低
                    cross_conversation_factor = 0.9 if conv_id != conversation_id else 1.0
                    final_score = similarity * time_decay * cross_conversation_factor
                    
                    if final_score >= self.similarity_threshold:
                        msg_copy = msg.copy()
                        msg_copy['_source_conversation'] = conv_id
                        all_results.append({
                            'message': msg_copy,
                            'score': final_score,
                            'similarity': similarity,
                            'time_decay': time_decay
                        })
        
        # 按得分排序
        all_results.sort(key=lambda x: x['score'], reverse=True)
        
        # 返回top-k
        final_results = [r['message'] for r in all_results[:self.retrieval_top_k]]
        
        # 统计跨对话检索结果
        cross_count = sum(1 for r in final_results if r.get('_source_conversation') != conversation_id)
        logger.info(f"跨对话检索完成: 找到 {len(all_results)} 个结果，返回 {len(final_results)} 个（其中 {cross_count} 个来自其他对话）")
        
        return final_results
    
    def build_context(self, 
                  conversation_id: str,
                  current_message: str,
                  conversation_history: List[Dict]) -> List[Dict]:
        """构建优化的上下文"""
        non_system_messages = [msg for msg in conversation_history if msg.get('role') != 'system']
        
        # 使用滑动窗口
        recent_messages = self._get_sliding_window(non_system_messages, self.max_recent_messages)
        
        # 验证：确保滑动窗口的第一个消息是user（不应该从assistant开始）
        if recent_messages and recent_messages[0].get('role') != 'user':
            logger.error(f"严重错误：滑动窗口第一个消息不是user！role: {recent_messages[0].get('role')}")
            logger.error(f"这会导致模型续写用户请求！")
            # 尝试修复：往前找user消息
            for i, msg in enumerate(non_system_messages):
                if msg.get('role') == 'user':
                    # 从找到的user开始，取最近的消息
                    start_idx = max(0, len(non_system_messages) - self.max_recent_messages + 1)
                    if i < start_idx:
                        start_idx = i
                    recent_messages = non_system_messages[start_idx:]
                    if len(recent_messages) > self.max_recent_messages - 1:
                        recent_messages = recent_messages[-(self.max_recent_messages - 1):]
                    logger.warning(f"已修复：从位置{i}的user消息开始")
                    break
        
        # 【关键修复】如果滑动窗口的最后一条是 user，从内存中补充对应的 assistant 回复
        if recent_messages and recent_messages[-1].get('role') == 'user':
            logger.warning("滑动窗口最后一条是user，尝试从内存中补充assistant回复")
            
            # 从内存中查找这条 user 消息后面的 assistant 回复
            if conversation_id in self.memory:
                memory_messages = self.memory[conversation_id]['messages']
                memory_non_system = [msg for msg in memory_messages if msg.get('role') != 'system']
                
                # 找到这条 user 消息在内存中的位置
                last_user_id = recent_messages[-1].get('id')
                if last_user_id:
                    for i, msg in enumerate(memory_non_system):
                        if msg.get('id') == last_user_id:
                            # 检查后面是否有 assistant 回复
                            if i + 1 < len(memory_non_system) and memory_non_system[i + 1].get('role') == 'assistant':
                                assistant_reply = memory_non_system[i + 1]
                                recent_messages.append(assistant_reply)
                                logger.info(f"已从内存补充assistant回复: {assistant_reply.get('id')}")
                                break
            
            # 如果仍然以 user 结尾，移除最后一条 user（因为 current_message 会作为新的 user 添加）
            if recent_messages and recent_messages[-1].get('role') == 'user':
                logger.warning("无法从内存补充assistant回复，移除最后一条user消息")
                recent_messages = recent_messages[:-1]
        
        # ... 其余代码保持不变
        
        recent_count = len(recent_messages)
        retrieved_messages = self.retrieve_relevant_messages(
            conversation_id, 
            current_message,
            exclude_recent_count=recent_count
        )
        
        # 构建系统消息
        base_system_content = "你是一位专业的心理医生，擅长倾听和提供建议。请用温和、理解、专业的方式与来访者交流。"
        
        if retrieved_messages:
            retrieved_sorted = sorted(
                retrieved_messages,
                key=lambda x: x.get('timestamp', x.get('created_at', ''))
            )
            
            retrieved_user_messages = [
                msg.get('content', '') 
                for msg in retrieved_sorted 
                if msg.get('role') == 'user'
            ][:3]
            
            if retrieved_user_messages:
                context_info = "[上下文背景：用户之前提到过以下相关话题，请基于这些信息理解用户的状态和情绪，但不要直接引用或重复这些内容。请用自己的话重新表达和回应。]\n"
                for i, msg_content in enumerate(retrieved_user_messages, 1):
                    content_preview = msg_content[:80] + "..." if len(msg_content) > 80 else msg_content
                    context_info += f"{i}. {content_preview}\n"
                context_info += "\n" + base_system_content
                system_content = context_info
            else:
                system_content = base_system_content
        else:
            system_content = base_system_content
        
        system_messages = [msg for msg in conversation_history if msg.get('role') == 'system']
        if not system_messages:
            system_messages = [{
                "role": "system",
                "content": system_content
            }]
        else:
            system_messages[0]['content'] = system_content
        
        # 组装最终上下文
        context_messages = []
        context_messages.extend(system_messages)
        context_messages.extend(recent_messages)
        
        # 添加当前用户消息
        context_messages.append({
            "role": "user",
            "content": current_message
        })
        
        # 最终验证
        if context_messages[-1].get('role') != 'user':
            logger.error(f"致命错误：最后一条消息不是user！")
            return []
        
        if len(context_messages) >= 2 and context_messages[-2].get('role') == 'user':
            logger.error(f"致命错误：出现连续的user消息！")
            logger.error(f"最后3条消息: {[msg.get('role') for msg in context_messages[-3:]]}")
            return []  # 直接拒绝，避免模型续写
        
        # 保存调试信息到debug.json（已关闭）
        # self._save_debug_info(conversation_id, current_message, context_messages, conversation_history)
        
        # 日志
        total_chars = sum(len(msg.get('content', '')) for msg in context_messages)
        estimated_tokens = total_chars * 1.5
        
        logger.info(f"上下文构建完成: {len(context_messages)} 条消息, 约 {int(estimated_tokens)} tokens")
        logger.info(f"  - 系统消息: {len(system_messages)}")
        logger.info(f"  - 检索到的历史: {len(retrieved_messages)}")
        logger.info(f"  - 滑动窗口消息: {len(recent_messages)}")
        logger.info(f"  - 最后一条消息role: {context_messages[-1].get('role')}")
        logger.info(f"  - 倒数第二条消息role: {context_messages[-2].get('role') if len(context_messages) >= 2 else 'N/A'}")
        
        return context_messages
    
    def _save_debug_info(self, conversation_id: str, current_message: str, 
                        context_messages: List[Dict], conversation_history: List[Dict]):
        """保存调试信息到debug.json"""
        try:
            # debug文件路径
            debug_path = os.path.join(os.path.dirname(self.storage_path), "debug.json")
            
            # 读取现有调试信息（如果存在）
            debug_data = []
            if os.path.exists(debug_path):
                try:
                    with open(debug_path, 'r', encoding='utf-8') as f:
                        debug_data = json.load(f)
                        if not isinstance(debug_data, list):
                            debug_data = []
                except:
                    debug_data = []
            
            # 构建调试信息
            debug_entry = {
                "timestamp": datetime.now().isoformat(),
                "conversation_id": conversation_id,
                "current_message": current_message,
                "context_messages": context_messages,
                "context_summary": {
                    "total_messages": len(context_messages),
                    "system_messages": len([m for m in context_messages if m.get('role') == 'system']),
                    "user_messages": len([m for m in context_messages if m.get('role') == 'user']),
                    "assistant_messages": len([m for m in context_messages if m.get('role') == 'assistant']),
                    "last_3_roles": [m.get('role') for m in context_messages[-3:]] if len(context_messages) >= 3 else [m.get('role') for m in context_messages],
                    "last_message_role": context_messages[-1].get('role') if context_messages else None,
                    "second_last_role": context_messages[-2].get('role') if len(context_messages) >= 2 else None,
                },
                "conversation_history_summary": {
                    "total_messages": len(conversation_history),
                    "non_system_messages": len([m for m in conversation_history if m.get('role') != 'system']),
                    "last_message_role": conversation_history[-1].get('role') if conversation_history else None,
                },
                "message_details": [
                    {
                        "index": i,
                        "role": msg.get('role'),
                        "content_preview": msg.get('content', '')[:100] + "..." if len(msg.get('content', '')) > 100 else msg.get('content', ''),
                        "content_length": len(msg.get('content', ''))
                    }
                    for i, msg in enumerate(context_messages)
                ]
            }
            
            # 添加到调试数据（只保留最近50条）
            debug_data.append(debug_entry)
            if len(debug_data) > 50:
                debug_data = debug_data[-50:]
            
            # 保存到文件
            with open(debug_path, 'w', encoding='utf-8') as f:
                json.dump(debug_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"调试信息已保存到: {debug_path}")
            
        except Exception as e:
            logger.warning(f"保存调试信息失败: {e}")
    
    def sync_conversation(self, conversation_id: str, messages: List[Dict], metadata: Optional[Dict] = None) -> bool:
        """同步对话（以前端数据为准，完全替换）"""
        try:
            backend_messages = []
            for msg in messages:
                backend_msg = {
                    "role": msg.get("role"),
                    "content": msg.get("content"),
                    "timestamp": msg.get("timestamp") or msg.get("updatedAt") or datetime.now().isoformat(),
                    "conversation_id": conversation_id
                }
                if "id" in msg:
                    backend_msg["id"] = msg["id"]
                backend_messages.append(backend_msg)
            
            self.memory[conversation_id] = {
                'messages': backend_messages,
                'metadata': metadata or {
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat(),
                    'message_count': len(backend_messages)
                }
            }
            
            if metadata:
                self.memory[conversation_id]['metadata'].update(metadata)
            self.memory[conversation_id]['metadata']['updated_at'] = datetime.now().isoformat()
            self.memory[conversation_id]['metadata']['message_count'] = len(backend_messages)
            
            # 重建FAISS索引
            self._build_faiss_index(conversation_id)
            
            self._save_memory()
            logger.info(f"已同步对话: {conversation_id}, 消息数量: {len(backend_messages)}")
            return True
        except Exception as e:
            logger.error(f"同步对话失败: {e}", exc_info=True)
            return False
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话"""
        if conversation_id in self.memory:
            del self.memory[conversation_id]
            if conversation_id in self.faiss_indices:
                del self.faiss_indices[conversation_id]
            if conversation_id in self.message_index_maps:
                del self.message_index_maps[conversation_id]
            self._save_memory()
            logger.info(f"已删除对话: {conversation_id}")
            return True
        return False
    
    def get_conversation_stats(self, conversation_id: str) -> Dict:
        """获取对话统计信息"""
        if conversation_id not in self.memory:
            return {}
        
        conv = self.memory[conversation_id]
        stats = {
            'message_count': len(conv['messages']),
            'metadata': conv.get('metadata', {})
        }
        
        if conversation_id in self.faiss_indices:
            stats['faiss_index_size'] = self.faiss_indices[conversation_id].ntotal
        
        return stats
    
    def initialize_indices(self):
        """初始化所有对话的FAISS索引（启动时调用）"""
        logger.info("开始初始化所有对话的FAISS索引...")
        for conv_id in self.memory.keys():
            self._build_faiss_index(conv_id)
        logger.info(f"FAISS索引初始化完成: {len(self.faiss_indices)} 个对话")


# 全局记忆管理器实例
_memory_manager = None

def get_memory_manager() -> MemoryManager:
    """获取全局记忆管理器实例"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
        # 初始化所有索引
        _memory_manager.initialize_indices()
    return _memory_manager
