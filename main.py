import sys
import os
import boto3
import uuid
from flask import Flask, request, jsonify
 import secure_filename
import threading
import time
import cv2
import numpy as np
from io import BytesIO
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # DON'T CHANGE THIS !!!

app = Flask(__name__)

# Configuração para acessar o LocalStack
ENDPOINT_URL = "http://localhost:4566"
S3_INPUT_BUCKET = "image-input"
S3_PROCESSED_BUCKET = "image-processed"
SQS_INPUT_QUEUE = "new-image-input.fifo"
SQS_PROCESSED_QUEUE = "new-image-processed.fifo"

# Inicializar clientes AWS
s3_client = boto3.client('s3', endpoint_url=ENDPOINT_URL)
sqs_client = boto3.client('sqs', endpoint_url=ENDPOINT_URL)

def get_queue_url(queue_name):
    """Obtém a URL da fila SQS pelo nome."""
    response = sqs_client.get_queue_url(QueueName=queue_name)
    return response['QueueUrl']

@app.route('/upload', methods=['POST'])
def upload_image():
    """Endpoint para upload de imagens."""
    if 'image' not in request.files:
        return jsonify({'error': 'Nenhuma imagem enviada'}), 400
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({'error': 'Nome de arquivo vazio'}), 400
    
    if not file.filename.lower().endswith('.png'):
        return jsonify({'error': 'Apenas imagens PNG são permitidas'}), 400
    
    try:
        # Gerar um ID único para a imagem
        image_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        object_key = f"{image_id}_{filename}"
        
        # Fazer upload da imagem para o bucket S3
        s3_client.upload_fileobj(file, S3_INPUT_BUCKET, object_key)
        
        # Enviar mensagem para a fila SQS
        queue_url = get_queue_url(SQS_INPUT_QUEUE)
        message_body = json.dumps({
            'image_id': image_id,
            'object_key': object_key
        })
        
        sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=message_body,
            MessageGroupId='image_processing',
            MessageDeduplicationId=image_id
        )
        
        return jsonify({
            'success': True,
            'message': 'Imagem enviada para processamento',
            'image_id': image_id,
            'object_key': object_key
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def process_image(image_data):
    """Processa a imagem usando OpenCV (binarização)."""
    # Converter bytes para imagem OpenCV
    nparr = np.frombuffer(image_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Aplicar binarização (exemplo de processamento)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    
    # Converter de volta para bytes
    is_success, buffer = cv2.imencode(".png", binary)
    if is_success:
        return BytesIO(buffer.tobytes())
    else:
        raise Exception("Falha ao processar a imagem")

def worker_process():
    """Worker para processar imagens da fila SQS."""
    print("Worker iniciado. Aguardando mensagens...")
    
    while True:
        try:
            # Obter URL da fila de entrada
            input_queue_url = get_queue_url(SQS_INPUT_QUEUE)
            
            # Receber mensagens da fila
            response = sqs_client.receive_message(
                QueueUrl=input_queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20  # Long polling
            )
            
            if 'Messages' in response:
                for message in response['Messages']:
                    try:
                        # Processar a mensagem
                        message_body = json.loads(message['Body'])
                        object_key = message_body['object_key']
                        image_id = message_body['image_id']
                        
                        print(f"Processando imagem: {object_key}")
                        
                        # Baixar a imagem do S3
                        response = s3_client.get_object(
                            Bucket=S3_INPUT_BUCKET,
                            Key=object_key
                        )
                        image_data = response['Body'].read()
                        
                        # Processar a imagem
                        processed_image = process_image(image_data)
                        
                        # Salvar a imagem processada no S3
                        processed_key = f"processed_{object_key}"
                        s3_client.upload_fileobj(
                            processed_image, 
                            S3_PROCESSED_BUCKET, 
                            processed_key
                        )
                        
                        # Enviar mensagem para a fila de processamento concluído
                        processed_queue_url = get_queue_url(SQS_PROCESSED_QUEUE)
                        processed_message = json.dumps({
                            'image_id': image_id,
                            'original_key': object_key,
                            'processed_key': processed_key
                        })
                        
                        sqs_client.send_message(
                            QueueUrl=processed_queue_url,
                            MessageBody=processed_message,
                            MessageGroupId='image_processing',
                            MessageDeduplicationId=f"processed_{image_id}"
                        )
                        
                        # Excluir a mensagem da fila após processamento
                        sqs_client.delete_message(
                            QueueUrl=input_queue_url,
                            ReceiptHandle=message['ReceiptHandle']
                        )
                        
                        print(f"Imagem {object_key} processada com sucesso")
                        
                    except Exception as e:
                        print(f"Erro ao processar mensagem: {str(e)}")
            
            # Pequena pausa para evitar consumo excessivo de CPU
            time.sleep(1)
            
        except Exception as e:
            print(f"Erro no worker: {str(e)}")
            time.sleep(5)  # Pausa maior em caso de erro

def start_worker():
    """Inicia o worker em uma thread separada."""
    worker_thread = threading.Thread(target=worker_process)
    worker_thread.daemon = True
    worker_thread.start()
    return worker_thread

if __name__ == '__main__':
    # Iniciar o worker em uma thread separada
    worker_thread = start_worker()
    
    # Iniciar a aplicação Flask
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
