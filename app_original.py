from flask import Flask, request, jsonify
from pinecone.vectorstore import retrieve_context
from bedrock.bedrock_llm import generate_story
from config import config

# Initialize configuration
config.initialize()

app = Flask(__name__)

@app.route("/generate-story", methods=["POST"])
def generate():
    data = request.get_json()
    core_idea = data.get("core_idea")
    style = data.get("style", "short_post")  # short_post, long_post, blog_post

    if not core_idea:
        return jsonify({"error": "Missing core_idea"}), 400

    context_chunks = retrieve_context(core_idea)
    story = generate_story(core_idea, context_chunks, style)
    return jsonify({"story": story})

if __name__ == "__main__":
    app.run(debug=config.FLASK_DEBUG, port=config.FLASK_PORT)
