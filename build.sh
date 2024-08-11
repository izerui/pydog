docker build -f Dockerfile -t pydog:1.0 .
docker tag pydog:1.0 harbor.yj2025.com/library/pydog:1.0
docker push harbor.yj2025.com/library/pydog:1.0