from flask import Flask, request, jsonify
import faiss
import numpy as np
import os
from flask_cors import CORS  # 🚀 Import CORS
from sentence_transformers import SentenceTransformer

app = Flask(__name__)
CORS(app)  # 🚀 Enable Cross-Origin Resource Sharing

# 🚀 Initialize embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")
d = model.get_sentence_embedding_dimension()  # Get model vector size

# 🚀 Use Cosine Similarity instead of L2 distance
index = faiss.IndexFlatIP(d)  # Inner Product = Cosine Similarity
index_file = "faiss_index.bin"
stored_texts_file = "stored_texts.npy"

# 🚀 Load saved embeddings if available
if os.path.exists(index_file) and os.path.exists(stored_texts_file):
    index = faiss.read_index(index_file)
    stored_texts = np.load(stored_texts_file, allow_pickle=True).tolist()
else:
    stored_texts = []

# 🚀 Normalize embeddings before storing
def normalize(vec):
    return vec / np.linalg.norm(vec)

@app.route("/delete-all", methods=["POST"])
def delete_all():
    global index, stored_texts
    index = faiss.IndexFlatIP(d)  # Reset index
    stored_texts = []
    if os.path.exists(index_file):
        os.remove(index_file)
    if os.path.exists(stored_texts_file):
        os.remove(stored_texts_file)
    return jsonify({"message": "✅ All embeddings deleted!"})

@app.route("/add-embedding", methods=["POST"])
def add_embedding():
    data = request.json
    text = data.get("text")

    if not text:
        return jsonify({"error": "Text is required"}), 400

    embedding = normalize(model.encode(text).astype(np.float32))  # 🚀 Normalize
    index.add(np.array([embedding]))  # Store embedding
    stored_texts.append(text)

    # 🚀 Save to disk for persistence
    faiss.write_index(index, index_file)
    np.save(stored_texts_file, np.array(stored_texts))

    return jsonify({"message": f"✅ Added embedding for '{text}'"})

@app.route("/query-embedding", methods=["POST"])
def query_embedding():
    data = request.json
    query = data.get("query")

    if not query:
        return jsonify({"error": "Query text is required"}), 400

    query_embedding = normalize(model.encode(query).astype(np.float32))  # 🚀 Normalize
    distances, indices = index.search(np.array([query_embedding]), k=1)

    if indices[0][0] == -1 or distances[0][0] < 0.5:  # 🚀 Ignore weak matches
        return jsonify({"message": "⚠️ No meaningful match found"})

    matched_text = stored_texts[indices[0][0]]
    similarity_score = float(distances[0][0])

    return jsonify({
        "query": query,
        "matched_text": matched_text,
        "similarity_score": similarity_score
    })

@app.route("/delete-text", methods=["POST"])
def delete_text():
    data = request.json
    text_to_delete = data.get("text")

    if not text_to_delete:
        return jsonify({"error": "Text is required"}), 400

    global stored_texts, index
    indices_to_remove = [i for i, text in enumerate(stored_texts) if text == text_to_delete]

    if not indices_to_remove:
        return jsonify({"message": f"⚠️ No matches found for '{text_to_delete}'"})

    # Remove matching texts
    stored_texts = [text for i, text in enumerate(stored_texts) if i not in indices_to_remove]

    # 🚀 Rebuild the index without deleted embeddings
    index = faiss.IndexFlatIP(d)
    for text in stored_texts:
        embedding = normalize(model.encode(text).astype(np.float32))
        index.add(np.array([embedding]))

    # 🚀 Save updated index
    faiss.write_index(index, index_file)
    np.save(stored_texts_file, np.array(stored_texts))

    return jsonify({"message": f"✅ Deleted all instances of '{text_to_delete}'"})

@app.route("/show-all", methods=["GET"])
def show_all():
    if not stored_texts:
        return jsonify({"message": "⚠️ No embeddings stored yet!"})

    return jsonify({"stored_values": stored_texts})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)