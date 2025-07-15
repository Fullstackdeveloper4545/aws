import ftplib
import os
import logging
import tempfile
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger()

class FTPManager:
    """Manages FTP operations"""
    
    def __init__(self, host: str, username: str, password: str, port: int = 21):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.ftp = None
    
    def connect(self) -> bool:
        """Connect to FTP server"""
        try:
            self.ftp = ftplib.FTP()
            self.ftp.connect(self.host, self.port)
            self.ftp.login(self.username, self.password)
            logger.info(f"Successfully connected to FTP server {self.host}")
            return True
        except Exception as e:
            logger.error(f"Error connecting to FTP server: {str(e)}")
            return False
    
    def disconnect(self):
        """Disconnect from FTP server"""
        if self.ftp:
            try:
                self.ftp.quit()
                logger.info("Disconnected from FTP server")
            except Exception as e:
                logger.error(f"Error disconnecting from FTP server: {str(e)}")
            finally:
                self.ftp = None
    
    def list_files(self, directory: str = "uploads") -> List[Dict]:
        """List files in the specified directory"""
        files = []
        try:
            if not self.ftp:
                if not self.connect():
                    return files
            
            # Change to the specified directory
            self.ftp.cwd(directory)
            
            # Get file list
            file_list = self.ftp.nlst()
            
            for filename in file_list:
                try:
                    # Get file size
                    size = self.ftp.size(filename)
                    files.append({
                        'filename': filename,
                        'size': size,
                        'directory': directory
                    })
                except Exception as e:
                    logger.warning(f"Could not get size for file {filename}: {str(e)}")
                    files.append({
                        'filename': filename,
                        'size': 0,
                        'directory': directory
                    })
            
            logger.info(f"Found {len(files)} files in FTP directory {directory}")
            return files
            
        except Exception as e:
            logger.error(f"Error listing files from FTP directory {directory}: {str(e)}")
            return files
    
    def download_file(self, filename: str, directory: str = "uploads") -> Optional[str]:
        """Download file from FTP and return content as string"""
        try:
            if not self.ftp:
                if not self.connect():
                    return None
            
            # Change to the specified directory
            self.ftp.cwd(directory)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w+b', delete=False) as temp_file:
                temp_path = temp_file.name
            
            try:
                # Download file to temporary location
                with open(temp_path, 'wb') as local_file:
                    self.ftp.retrbinary(f'RETR {filename}', local_file.write)
                
                # Read file content
                with open(temp_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                logger.info(f"Successfully downloaded file from FTP: {directory}/{filename}")
                return content
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.error(f"Error downloading file {filename} from FTP: {str(e)}")
            return None
    
    def move_file(self, filename: str, source_dir: str = "uploads", dest_dir: str = "processed") -> bool:
        """Move file from source directory to destination directory"""
        try:
            if not self.ftp:
                if not self.connect():
                    return False
            
            # Create destination directory if it doesn't exist
            try:
                self.ftp.cwd(dest_dir)
            except ftplib.error_perm:
                # Directory doesn't exist, create it
                self.ftp.mkd(dest_dir)
            
            # Change to source directory
            self.ftp.cwd(source_dir)
            
            # Rename file (move it)
            new_path = f"{dest_dir}/{filename}"
            self.ftp.rename(filename, new_path)
            
            logger.info(f"Successfully moved file {filename} from {source_dir} to {dest_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Error moving file {filename} from {source_dir} to {dest_dir}: {str(e)}")
            return False
    
    def delete_file(self, filename: str, directory: str = "uploads") -> bool:
        """Delete file from FTP server"""
        try:
            if not self.ftp:
                if not self.connect():
                    return False
            
            # Change to the specified directory
            self.ftp.cwd(directory)
            
            # Delete file
            self.ftp.delete(filename)
            
            logger.info(f"Successfully deleted file {filename} from {directory}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file {filename} from {directory}: {str(e)}")
            return False
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect() 