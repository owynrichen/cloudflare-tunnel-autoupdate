FROM python:3.12-slim
WORKDIR /src
COPY . /src
RUN pip install --upgrade pip && pip install uv pytest python-dotenv requests PyYAML
CMD ["uv", "test"]
