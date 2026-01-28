FROM eclipse-temurin:17-jdk-jammy

# Installation de Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/bin/python3 /usr/bin/python

WORKDIR /app

# Copier les requirements et installer les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY config.py .
COPY src/ ./src/
COPY data/ ./data/

# Variables d'environnement Spark
ENV PYSPARK_PYTHON=python3
ENV PYSPARK_DRIVER_PYTHON=python3

# Port pour Spark UI
EXPOSE 4040
# Port pour l'API FastAPI
EXPOSE 8000

# Commande par défaut
CMD ["python", "src/main.py"]
