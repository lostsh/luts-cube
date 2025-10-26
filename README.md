Run the container

> This is deprecated but stil works just deprecated
docker run --rm -it -v ./:/home/ubuntu/vol:z magick /bin/bash
docker run --rm -it -v /home/lostsh/Pictures/test-docker/dkvol/:/home/ubuntu/vol:z magick


> use absolute path (for now)

./run.sh -p "/home/lostsh/Pictures/test-docker/100MSDCF/DSC08876.JPG" -c "/home/lostsh/Downloads/FuturisticHarborLook.cube" -o "/home/lostsh/Pictures/test-docker/76.jpg"


# Todo :

- [x] Make a wrapper for the new docker image

the wraper take the input : 

if signle file : 
    - start container and simply process with attached volume to directory and signle file mode with args
if file list / direcotry is given
    - start container mount the directory or multiples dirs maybe ? and the process the files in list mode from inside the container

use CMD the container is on its own script inside handle usecases
the wrapper outside handle the interface details

- [x] clean up remove the container

- [ ] Improve the attachment system in order to process batch files