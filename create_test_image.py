import cv2
import numpy as np
from PIL import Image

# Criar uma imagem de teste simples
width, height = 300, 200
image = np.ones((height, width, 3), dtype=np.uint8) * 255  # Imagem branca

# Desenhar algumas formas para teste
cv2.rectangle(image, (50, 50), (250, 150), (0, 0, 255), -1)  # Retângulo vermelho
cv2.circle(image, (150, 100), 50, (0, 255, 0), 5)  # Círculo verde

# Salvar a imagem como PNG
cv2.imwrite('test_image.png', image)

print("Imagem de teste criada com sucesso: test_image.png")
