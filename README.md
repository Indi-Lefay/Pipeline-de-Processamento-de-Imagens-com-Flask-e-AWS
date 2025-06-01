# Pipeline-de-Processamento-de-Imagens-com-Flask-e-AWS

Este projeto implementa um pipeline de processamento de imagens utilizando Flask e serviços AWS simulados via LocalStack. O sistema permite que clientes enviem imagens PNG via API, que são armazenadas no S3, processadas com OpenCV e notificadas via filas SQS.

## Estrutura do Projeto

```
image_processing_pipeline/
├── venv/                      # Ambiente virtual Python
├── src/                       # Código fonte da aplicação
│   ├── main.py                # Aplicação Flask principal (API + worker)
│   ├── routes/                # Rotas da API
│   ├── models/                # Modelos de dados
│   └── static/                # Arquivos estáticos
├── docker-compose.yml         # Configuração do LocalStack
├── requirements.txt           # Dependências do projeto
├── setup_aws_resources.py     # Script para criar recursos AWS no LocalStack
├── start_localstack.sh        # Script para iniciar o LocalStack
├── start_app.sh               # Script para iniciar a aplicação Flask
├── create_test_image.py       # Script para criar imagem de teste
└── test_upload.sh             # Script para testar o upload de imagem
```

## Requisitos

- Python 3.11+
- Docker e Docker Compose
- LocalStack

## Dependências

- Flask: Framework web
- Boto3: SDK AWS para Python
- OpenCV: Biblioteca de processamento de imagens
- Pillow: Biblioteca de manipulação de imagens
- LocalStack: Emulador de serviços AWS

## Configuração e Execução

### 1. Configuração do Ambiente

Clone o repositório e configure o ambiente virtual:

```bash
# Criar e ativar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### 2. Iniciar o LocalStack e Configurar Recursos AWS

```bash
# Iniciar o LocalStack e criar recursos AWS
./start_localstack.sh
```

Este script inicia o LocalStack via Docker Compose e cria:
- Buckets S3: `image-input` e `image-processed`
- Filas SQS FIFO: `new-image-input.fifo` e `new-image-processed.fifo`

### 3. Iniciar a Aplicação Flask

```bash
# Iniciar a aplicação Flask (API + worker)
./start_app.sh
```

A aplicação estará disponível em `http://localhost:5000`.

## Fluxo de Funcionamento

1. **Upload de Imagem**:
   - Cliente envia imagem PNG para o endpoint `/upload`
   - Imagem é armazenada no bucket S3 `image-input`
   - Mensagem é enviada para a fila SQS `new-image-input.fifo`

2. **Processamento de Imagem**:
   - Worker realiza polling na fila `new-image-input.fifo`
   - Ao receber mensagem, recupera a imagem do bucket S3 `image-input`
   - Processa a imagem com OpenCV (binarização)
   - Salva a imagem processada no bucket S3 `image-processed`
   - Envia mensagem para a fila SQS `new-image-processed.fifo`

## Testando o Pipeline

1. **Criar Imagem de Teste**:
```bash
python create_test_image.py
```

2. **Testar o Upload**:
```bash
./test_upload.sh
```

## Detalhes da Implementação

### API Flask

A API Flask expõe um endpoint `/upload` que aceita requisições POST com imagens PNG. O endpoint valida a imagem, gera um ID único, faz upload para o S3 e envia uma mensagem para a fila SQS.

### Worker

O worker é executado em uma thread separada dentro da mesma aplicação Flask. Ele realiza polling contínuo na fila SQS, processa as imagens recebidas e envia notificações de conclusão.

### Processamento de Imagem

O processamento de imagem utiliza OpenCV para aplicar uma binarização simples na imagem original, convertendo-a para preto e branco.

## Observações

- Todas as filas SQS são do tipo FIFO (First-In-First-Out)
- O sistema utiliza IDs únicos (UUID) para rastrear imagens durante todo o pipeline
- O LocalStack simula os serviços AWS localmente, sem necessidade de credenciais reais
- O worker e a API são executados no mesmo processo para simplificar a implantação
