import boto3
import json
from pathlib import Path
from jinja2 import Template
from config import config

def get_bedrock_client():
    return boto3.client("bedrock-runtime", region_name=config.AWS_REGION)

def load_prompt(enhanced=True):
    """Load story generation prompt template
    
    Args:
        enhanced: If True, use enhanced prompt for better quality
    """
    if enhanced and (config.PROMPTS_DIR / "enhanced_story_prompt.txt").exists():
        prompt_path = config.PROMPTS_DIR / "enhanced_story_prompt.txt"
    else:
        prompt_path = config.PROMPTS_DIR / "story_prompt.txt"
    
    with open(prompt_path) as f:
        return Template(f.read())

def generate_story(core_idea, retrieved_chunks, style, enhanced=True):
    """Generate a Richmond story using Claude
    
    Args:
        core_idea: The main story idea
        retrieved_chunks: Richmond context from vector search
        style: Story format (short_post, long_post, blog_post)
        enhanced: Use enhanced prompt for better quality
    """
    prompt_template = load_prompt(enhanced=enhanced)
    rendered_prompt = prompt_template.render(
        core_idea=core_idea, 
        retrieved_chunks=retrieved_chunks, 
        style=style
    )

    client = get_bedrock_client()
    response = client.invoke_model(
        modelId=config.BEDROCK_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "prompt": rendered_prompt,
            "max_tokens": config.TOKEN_LIMITS.get(style, config.TOKEN_LIMITS["short_post"]),
            "temperature": config.DEFAULT_TEMPERATURE,
        })
    )
    return json.loads(response["body"].read())["completion"]
