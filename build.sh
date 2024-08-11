docker build -f Dockerfile -t pydog:1.1 .
docker tag pydog:1.1 izerui/pydog:1.1
docker push izerui/pydog:1.1