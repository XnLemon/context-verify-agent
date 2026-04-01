# Knowledge Base

这里存放合同校审相关的知识资料。

## 目录说明

推荐按以下方式组织：

- `laws/`: 法律法规、司法解释、标准法条文本
- `ingested/`: 入库后的清单和向量索引产物

当前项目在线检索默认只使用：

- `knowledge/ingested/laws_faiss`

不支持让外部用户动态指定其他知识库目录。

## 推荐文件格式

首期建议优先放置 UTF-8 编码的 `.txt` 法律文本，便于切分和入库。

示例：

- `民法典.txt`
- `采购合同审查指引.txt`

## 入库产物

执行入库命令后，通常会生成：

- `knowledge/ingested/laws_chunks.jsonl`: 切分后的知识块清单
- `knowledge/ingested/laws_faiss/`: FAISS 向量索引目录

## 安全说明

当前知识库加载依赖 FAISS 本地索引恢复能力，只适合加载本地受信任来源构建的索引。
不要把不可信来源的索引目录直接放入 `knowledge/ingested/laws_faiss` 使用。
