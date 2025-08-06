from PIL import Image
import io
import boto3

def convert_to_supported_format(s3_bucket, s3_key):
    """Convert unsupported image formats to PNG"""
    
    if not s3_key.lower().endswith(('.gif', '.avif', '.webp')):
        return s3_key  # Already supported
    
    s3_client = boto3.client('s3')
    
    # Download original
    response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
    image_data = response['Body'].read()
    
    # Convert to PNG
    image = Image.open(io.BytesIO(image_data))
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Save as PNG
    png_buffer = io.BytesIO()
    image.save(png_buffer, format='PNG')
    png_buffer.seek(0)
    
    # Upload converted image
    new_key = s3_key.rsplit('.', 1)[0] + '_converted.png'
    s3_client.put_object(
        Bucket=s3_bucket,
        Key=new_key,
        Body=png_buffer.getvalue(),
        ContentType='image/png'
    )
    
    return new_key