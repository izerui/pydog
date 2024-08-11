docker build -f Dockerfile -t pydog:1.0 .
docker tag pydog:1.0 izerui/pydog:1.0
docker push izerui/pydog:1.0