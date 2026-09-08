import weaviate
import os, json

# Best practice: store your credentials in environment variables
weaviate_url="https://ccfs5vcsr26drqpfyzwcrg.c0.us-east-1.aws.weaviate.cloud"
weaviate_api_key = "Q0UrMzlVcXYzVDJDYk42dV9rcVBzTFR0SUZ5ZUxGQjZIQmdCYWJBNENLaGVYeFZ4d1RLRmJrbVhOeUtZPV92MjAw"

# Step 2.1: Connect to your Weaviate Cloud instance
with weaviate.connect_to_weaviate_cloud(
    cluster_url=weaviate_url,
    auth_credentials=weaviate_api_key,
) as client:

    # Step 2.2: Use this collection
    movies = client.collections.use("Movie")

    # Step 2.3: Perform a semantic search with NearText
    response = movies.query.near_text(
        query="sci-fi",
        limit=2
    )

    for obj in response.objects:
        print(json.dumps(obj.properties, indent=2))  # Inspect the results