# Student Planner server image. Python publishes multi-arch images, including linux/s390x
# (IBM LinuxONE), so the same file builds there unchanged:
#   docker build -t student-planner .                  (on a LinuxONE guest it builds for s390x)
#   docker run --rm -v planner-data:/data student-planner adduser alice
#   docker run -d --name planner -p 8765:8765 -v planner-data:/data \
#          -e PLANNER_TZ=Australia/Melbourne student-planner
FROM python:3.12-slim

# WITH_CRYPTO=1 adds database encryption of calendar URLs. On s390x, pip may need to compile
# the 'cryptography' package from source if no wheel is available for your Python version.
ARG WITH_CRYPTO=0
ENV PYTHONUNBUFFERED=1 PLANNER_DB=/data/planner.db PLANNER_HOST=0.0.0.0 PLANNER_PORT=8765

RUN pip install --no-cache-dir tzdata \
 && if [ "$WITH_CRYPTO" = "1" ]; then pip install --no-cache-dir cryptography; fi \
 && useradd --system --create-home planner \
 && mkdir /data && chown planner /data

WORKDIR /app
COPY planner_core.py panzer_planner_server /app/
USER planner
VOLUME /data
EXPOSE 8765

# (the health check assumes plain HTTP inside the container; terminate TLS in a reverse proxy)
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import os,urllib.request as u; u.urlopen('http://127.0.0.1:%s/api/health' % os.environ['PLANNER_PORT'], timeout=3)"

ENTRYPOINT ["python", "/app/panzer_planner_server"]
CMD ["serve"]