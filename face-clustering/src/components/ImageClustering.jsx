import React, { useState } from 'react';
import { FaDownload, FaUpload } from 'react-icons/fa';
import '../styles/ImageClustering.css';

const API_BASE_URL = 'http://localhost:8000/api';

const ImageClustering = () => {
  const [zipFile, setZipFile] = useState(null);
  const [queryImage, setQueryImage] = useState(null);
  const [similarImages, setSimilarImages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [uploadedImages, setUploadedImages] = useState([]);

  const handleZipUpload = async (event) => {
    const file = event.target.files[0];
    if (file && file.name.toLowerCase().endsWith('.zip')) {
      setLoading(true);
      setError(null);
      const formData = new FormData();
      formData.append('zipFile', file);
      
      try {
        const response = await fetch(`${API_BASE_URL}/upload/`, {
          method: 'POST',
          body: formData,
        });
        const data = await response.json();
        
        if (response.ok) {
          setZipFile(file);
          setUploadedImages(data.extracted_images);
          setError(null);
        } else {
          setError(data.error || 'Error uploading ZIP file');
        }
      } catch (error) {
        setError('Network error while uploading ZIP file');
      } finally {
        setLoading(false);
      }
    } else {
      setError('Please upload a valid ZIP file');
    }
  };

  const handleQueryImageUpload = async (event) => {
    const file = event.target.files[0];
    if (file && file.type.startsWith('image/')) {
      setLoading(true);
      setError(null);
      const formData = new FormData();
      formData.append('queryImage', file);
      
      try {
        const response = await fetch(`${API_BASE_URL}/upload/`, {
          method: 'POST',
          body: formData,
        });
        const data = await response.json();
        
        if (response.ok) {
          setQueryImage(file);
          setSimilarImages(data.matches || []);
          setError(null);
        } else {
          setError(data.error || 'Error uploading query image');
          setSimilarImages([]);
        }
      } catch (error) {
        setError('Network error while uploading query image');
        setSimilarImages([]);
      } finally {
        setLoading(false);
      }
    } else {
      setError('Please upload a valid image file');
    }
  };

  return (
    <div className="image-clustering-container">
      <header className="header">
        <h1>Image Identifier</h1>
        <button className="download-btn">
          <FaDownload /> Download Results
        </button>
      </header>

      {error && <div className="error-message">{error}</div>}
      {loading && <div className="loading">Processing...</div>}

      <div className="upload-section">
        <div className="upload-box">
          <input
            type="file"
            accept=".zip"
            onChange={handleZipUpload}
            id="zip-upload"
            className="file-input"
          />
          <label htmlFor="zip-upload" className="upload-label">
            <FaUpload /> Upload Image Folder (ZIP)
          </label>
          {zipFile && <p className="file-name">{zipFile.name}</p>}
          {uploadedImages.length > 0 && (
            <p className="upload-info">{uploadedImages.length} images extracted</p>
          )}
        </div>

        <div className="upload-box">
          <input
            type="file"
            accept="image/*"
            onChange={handleQueryImageUpload}
            id="query-upload"
            className="file-input"
          />
          <label htmlFor="query-upload" className="upload-label">
            <FaUpload /> Upload Query Image
          </label>
          {queryImage && <p className="file-name">{queryImage.name}</p>}
        </div>
      </div>

      <div className="results-section">
        <h2>Similar Images</h2>
        <div className="similar-images-grid">
          {similarImages.length === 0 ? (
            <p className="no-images">Upload a query image to see similar images</p>
          ) : (
            similarImages.map((image, index) => (
              <div key={index} className="image-card">
                <img 
                  src={`http://localhost:8000${image.url}`} 
                  alt={`Similar image ${index + 1}`}
                  onError={(e) => {
                    e.target.onerror = null;
                    e.target.src = 'https://via.placeholder.com/150?text=Image+Not+Found';
                  }}
                />
                <div className="image-info">
                  <p className="image-name">{image.name}</p>
                  <p className="similarity-score">Similarity: {image.similarity}%</p>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default ImageClustering;
