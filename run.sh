#!/bin/bash

# Short docker wrapper

DOCKER_IMAGE="lutsapply"
DOCKER_HOME="/home/user"

# $1: input picture
# $2: input LUT file .cube
# $3: output file
function launch_docker_convertion(){
    # Checking in input args
    #if [ $# -gt 0 ] && [ -d "$1" ]; then; fi

    # Check for image presence
    if [ -z "$(docker images -q ${DOCKER_IMAGE})" ]; then
        echo -e "[ > ]\tDocker Building Image"
        docker build -t ${DOCKER_IMAGE} . 2>/dev/null
        [[ $? == 0 ]] && echo -e "[ + ]\tDocker Image Build Success" \
        || echo -e "[ ! ]\tDocker Image Build Failed"
    fi

    # Convert path to path for the docker container
    pic="$(echo $1 | sed "s-${HOME}-${DOCKER_HOME}-g")"
    lut="$(echo $2 | sed "s-${HOME}-${DOCKER_HOME}-g")"
    out="$(echo $3 | sed "s-${HOME}-${DOCKER_HOME}-g")"

    # Runing the converter
    echo -e "[ = ]\tStarting Container to apply files"
    docker run --rm -it -v ${HOME}:/home/user/:z -e PIC="$pic" -e CUBE="$lut" -e OUT="$out" ${DOCKER_IMAGE}
    [[ $? == 0 ]] && echo -e "[ + ]\tSuccess" || echo -e "\n[ ! ]\tFailed"

    # Removing the image
    #[ -z "$(docker images -q ${DOCKER_IMAGE})" ] || docker rmi ${DOCKER_IMAGE} >/dev/null
}


picture_file=""
lut_cube_file=""
out_file=""
while [ -n "$1" ]; do
    case $1 in
        "-h" | "--help")
            print_usage
        ;;
        "-c" | "--cube")
            lut_cube_file="$2"
            shift
        ;;
        "-p" | "--picture")
            picture_file="$2"
            shift
        ;;
        "-o" | "--output")
            out_file="$2"
            shift
        ;;
        *)
            help "Wrong argument $1"
        ;;
    esac
    shift #next argument
done

echo -e "[ > ]\tDocker cube LUT applyer"

# Execute single file script mode
[[ "$lut_cube_file" != "" ]] \
&& [[ "$picture_file" != "" ]] \
&& [[ "$out_file" != "" ]] \
&& launch_docker_convertion ${picture_file} ${lut_cube_file} ${out_file}\
&& echo -e "\t[ ^ ] OK"

echo -e "[ _ ]\tBye"