# fileupload/face_clustering.py

import os
import cv2
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import normalize
from insightface.app import FaceAnalysis
from sklearn.decomposition import PCA
from sklearn.cluster import AgglomerativeClustering, SpectralClustering, AffinityPropagation
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score
from sklearn.metrics.pairwise import cosine_similarity

import matplotlib.pyplot as plt

app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0)

# Global shared variables
image_data = []
X_final = None
labels = None
pca = None

def process_zip_folder(image_folder):
    global image_data, X_final, labels, pca
    image_data = []

    for img_name in os.listdir(image_folder):
        img_path = os.path.join(image_folder, img_name)
        img = cv2.imread(img_path)
        if img is None:
            continue

        faces = app.get(img)
        if not faces:
            continue

        embeddings = [face.embedding for face in faces]
        image_data.append({
            'img_path': img_path,
            'img': img,
            'faces': faces,
            'embeddings': embeddings
        })

    all_embeddings = []
    for data in image_data:
        all_embeddings.extend(data['embeddings'])

    X = np.array(all_embeddings)
    X_norm = normalize(X, norm="l2")

    pca = PCA(n_components=75, random_state=42)
    X_pca = pca.fit_transform(X_norm)
    X_final = X_pca

    # Choose best clustering method
    cluster_algorithms = []

    agg = AgglomerativeClustering(n_clusters=20, metric='cosine', linkage='average')
    agg_labels = agg.fit_predict(X_final)
    cluster_algorithms.append(('Agglomerative', agg_labels, silhouette_score(X_final, agg_labels, metric='cosine')))

    spec = SpectralClustering(n_clusters=20, affinity='nearest_neighbors', random_state=42)
    spec_labels = spec.fit_predict(X_final)
    cluster_algorithms.append(('Spectral', spec_labels, silhouette_score(X_final, spec_labels, metric='cosine')))

    aff = AffinityPropagation(random_state=42)
    aff_labels = aff.fit_predict(X_final)
    cluster_algorithms.append(('AffinityPropagation', aff_labels, silhouette_score(X_final, aff_labels, metric='cosine')))

    # Best DBSCAN
    results = []
    for eps in np.arange(0.3, 0.6, 0.025):
        for min_samples in range(2, 7):
            db = DBSCAN(eps=eps, min_samples=min_samples, metric='cosine')
            lbls = db.fit_predict(X_final)
            if len(set(lbls)) > 1:
                sil = silhouette_score(X_final, lbls, metric='cosine')
                results.append((eps, min_samples, sil, lbls))

    if results:
        best = max(results, key=lambda x: x[2])
        cluster_algorithms.append(('DBSCAN', best[3], best[2]))

    best_algo = max(cluster_algorithms, key=lambda x: x[2])
    labels = best_algo[1]

    # Assign labels back to each image
    idx = 0
    for data in image_data:
        n = len(data['embeddings'])
        data['labels'] = labels[idx:idx + n]
        idx += n

def match_query_image(query_path):
    global image_data, X_final, labels, pca

    query_img = cv2.imread(query_path)
    query_faces = app.get(query_img)
    if not query_faces:
        return {'error': 'No face detected in query image'}

    query_embedding = query_faces[0].embedding.reshape(1, -1)
    query_norm = normalize(query_embedding, norm='l2')
    query_pca = pca.transform(query_norm)

    similarities = cosine_similarity(query_pca, X_final)[0]
    sorted_indices = np.argsort(similarities)[::-1]

    matched_images = []
    used_paths = set()

    for idx in sorted_indices:
        sim = similarities[idx]
        if sim < 0.55:
            break

        label = labels[idx]
        for data in image_data:
            if data['img_path'] in used_paths:
                continue
            if label in data['labels']:
                matched_images.append({
                    'image': os.path.basename(data['img_path']),
                    'similarity': float(sim)
                })
                used_paths.add(data['img_path'])
                break
        if len(matched_images) >= 20:
            break

    return matched_images
