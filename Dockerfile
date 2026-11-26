FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY openprospect ./openprospect
RUN pip install --no-cache-dir .[ai]
ENV ZERO_HAWK_HOME=/data
VOLUME /data
EXPOSE 5555
# Run: docker run -p 127.0.0.1:5555:5555 -v zh-data:/data zero-hawk
CMD ["zero-hawk","dashboard"]
