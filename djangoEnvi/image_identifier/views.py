from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
import os
import zipfile
from django.conf import settings
import logging
import tempfile

from .face_clustering import process_zip_folder, match_query_image

logger = logging.getLogger(__name__)

@csrf_exempt
def handle_upload(request):
    if request.method == 'POST':
        try:
            print("\n=== Starting File Upload Process ===")
            
            # Handle ZIP file upload
            if 'zipFile' in request.FILES:
                zip_file = request.FILES['zipFile']
                print(f"\n[ZIP Upload] Received ZIP file: {zip_file.name}")
                
                # Create a temporary file to store the ZIP
                with tempfile.NamedTemporaryFile(delete=False) as temp_zip:
                    for chunk in zip_file.chunks():
                        temp_zip.write(chunk)
                    temp_zip_path = temp_zip.name
                
                try:
                    # Create necessary directories
                    upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', zip_file.name.split('.')[0])
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    # Save the ZIP file
                    zip_path = default_storage.save(f'uploads/{zip_file.name}', zip_file)
                    
                    # Extract ZIP contents
                    with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                        print("\n[ZIP Contents] Files in ZIP:")
                        for file_info in zip_ref.infolist():
                            print(f"  - {file_info.filename} ({file_info.file_size} bytes)")

                        # Extract only top-level image files
                        for member in zip_ref.infolist():
                            if member.is_dir():
                                continue  # Skip folders
                            
                            filename = os.path.basename(member.filename)
                            if not filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                                continue  # Skip non-image files
                            
                            # Extract top-level image file
                            with zip_ref.open(member) as source_file:
                                target_path = os.path.join(upload_dir, filename)
                                with open(target_path, "wb") as target_file:
                                    target_file.write(source_file.read())
                            print(f"[Extracted] {filename}")
                    
                    # Get list of extracted images
                    extracted_images = [f for f in os.listdir(upload_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
                    print(f"\n[ZIP Upload] Found {len(extracted_images)} images")
                    
                    # Run clustering process on uploaded images
                    process_zip_folder(upload_dir)

                    return JsonResponse({
                        'message': 'ZIP file uploaded, extracted and processed successfully',
                        'extracted_images': extracted_images,
                        'upload_dir': upload_dir
                    })

                finally:
                    # Clean up the temporary file
                    if os.path.exists(temp_zip_path):
                        os.unlink(temp_zip_path)
                
            # Handle query image upload
            elif 'queryImage' in request.FILES:
                query_image = request.FILES['queryImage']
                print(f"\n[Query Image] Received image: {query_image.name}")
                
                # Create query directory and save image
                query_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', 'query')
                os.makedirs(query_dir, exist_ok=True)
                image_path = default_storage.save(f'uploads/query/{query_image.name}', query_image)
                full_image_path = os.path.join(settings.MEDIA_ROOT, image_path)
                
                print(f"Processing query image at: {full_image_path}")
                
                # Match the query image against clustered images
                try:
                    matched = match_query_image(full_image_path)
                    print(f"Matched images: {matched}")
                    
                    if matched is None:
                        return JsonResponse({'error': 'No face detected in the query image'}, status=400)
                    
                    # Convert matched image paths to URLs
                    matched_images = []
                    for match in matched:
                        if isinstance(match, dict):
                            # Get image name and similarity score
                            image_name = match.get('image', '')
                            similarity = match.get('similarity', 0)
                            
                            if not image_name:
                                continue
                                
                            # Find the upload directory containing the images
                            upload_dirs = [d for d in os.listdir(os.path.join(settings.MEDIA_ROOT, 'uploads')) 
                                        if os.path.isdir(os.path.join(settings.MEDIA_ROOT, 'uploads', d)) 
                                        and d != 'query']
                            
                            if not upload_dirs:
                                continue
                                
                            # Use the first upload directory found
                            upload_dir = upload_dirs[0]
                            
                            # Create URL for the image
                            image_url = f'/media/uploads/{upload_dir}/{image_name}'
                            matched_images.append({
                                'url': image_url,
                                'name': image_name,
                                'similarity': round(similarity * 100, 2)  # Convert to percentage
                            })

                    print(f"Processed {len(matched_images)} matched images")
                    return JsonResponse({
                        'message': 'Query image processed successfully',
                        'matches': matched_images
                    })
                    
                except Exception as e:
                    print(f"Error during image matching: {str(e)}")
                    return JsonResponse({'error': f'Error processing query image: {str(e)}'}, status=500)

            return JsonResponse({'error': 'No file uploaded'}, status=400)

        except Exception as e:
            print(f"\n[ERROR] {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)
