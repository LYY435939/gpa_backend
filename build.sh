docker build -t gpa . --network=host
docker stop gpa
docker rm -f gpa
docker run -d -p 1120:8000 --name gpa gpa