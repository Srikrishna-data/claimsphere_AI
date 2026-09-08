import weaviate
from weaviate.classes.config import Configure
import os

# Best practice: store your credentials in environment variables
weaviate_url="https://ccfs5vcsr26drqpfyzwcrg.c0.us-east-1.aws.weaviate.cloud"
weaviate_api_key = "Q0UrMzlVcXYzVDJDYk42dV9rcVBzTFR0SUZ5ZUxGQjZIQmdCYWJBNENLaGVYeFZ4d1RLRmJrbVhOeUtZPV92MjAw"

# Step 1.1: Connect to your Weaviate Cloud instance
with weaviate.connect_to_weaviate_cloud(
    cluster_url=weaviate_url,
    auth_credentials=weaviate_api_key,
) as client:

    # Step 1.2: Create a collection
    movies = client.collections.create(
        name="Movie",
        vector_config=Configure.Vectors.text2vec_weaviate(),  # Configure the Weaviate Embeddings vectorizer
    )

    # Step 1.3: Import three objects
    data_objects = [
        {"title": "The Matrix", "description": "A computer hacker learns about the true nature of reality and his role in the war against its controllers.", "genre": "Science Fiction"},
        {"title": "Spirited Away", "description": "A young girl becomes trapped in a mysterious world of spirits and must find a way to save her parents and return home.", "genre": "Animation"},
        {"title": "The Lord of the Rings: The Fellowship of the Ring", "description": "A meek Hobbit and his companions set out on a perilous journey to destroy a powerful ring and save Middle-earth.", "genre": "Fantasy"},
    ]

    movies = client.collections.use("Movie")
    movies.data.ingest(data_objects)

    print(f"Imported & vectorized {len(movies)} objects into the Movie collection")