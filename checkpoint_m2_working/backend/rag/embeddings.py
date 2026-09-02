import os
import boto3
from langchain_aws import BedrockEmbeddings


def get_embeddings() -> BedrockEmbeddings:
    client = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))
    return BedrockEmbeddings(
        client=client,
        model_id=os.getenv("EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0"),
    )
