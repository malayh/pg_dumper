FROM python:3.10.15-slim-bookworm

# Install PostgreSQL client
RUN apt update;\
    apt install -y postgresql-common; \
    YES=y /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh; \
    apt -y install postgresql-client-17;


# Install Python dependencies
RUN mkdir /pg_dumper
WORKDIR /pg_dumper
COPY . . 
RUN pip install -r requirements.txt

ENTRYPOINT ["python", "/pg_dumper/main.py"]
CMD ["--config /pg_dumper/config.yml"]
