#!/bin/sh
## Author: lostsh
##
## Script to apply .cube LUT file to a picture
##

echo -e "\t[+] Apply LUT file in .cube format to picture\n"

print_usage (){
    echo -e "\t[?] Usage:\t$0 -c lut_file.cube -p picture.jpg"
    echo -e "\t\t\t-o output_file.jpg"
    echo -e "\t\t\tls files.jpg | $0 lut_file.cube"
    if [ $# -gt 0 ]; then
        echo -e "\t[!] $1" >&2
        exit;
    fi
}

[ $# -lt 1 ] && print_usage "Missing LUT (.cube) file"
echo -e "\t[ = ] Run"


#	##==============##
#	## Main section ##
#	##______________##
if [ $# -lt 2 ]; then
    lut_file="$1"
    shift
    while read -r input_pic; do
        ffmpeg -y -i $input_pic -vf lut3d=$lut_file "n_$input_pic"
        [[ $? == 0 ]] && echo -e "\t[ ^ ] $input_pic\t OK" || echo -e "\t[ v ] $input_pic\t KO"
    done
fi

lut_file=""
picture_file=""
output_file=""
# switch mode from signle file to list
while [ -n "$1" ]; do
    case $1 in
        "-h" | "--help")
            print_usage
        ;;
        "-c" | "--cube")
            lut_file="$2"
            shift
        ;;
        "-p" | "--picture")
            picture_file="$2"
            shift
        ;;
        "-o" | "--output")
            output_file="$2"
            shift
        ;;
        *)
            help "Wrong argument $1"
        ;;
    esac
    shift #next argument
done

# Execute single file script mode
[[ "$lut_file" != "" ]] \
&& [[ "$picture_file" != "" ]] \
&& [[ "$output_file" != "" ]] \
&& ffmpeg -y -i $picture_file -vf lut3d=$lut_file "$output_file" \
&& echo -e "\t[ ^ ] OK"

echo -e "\t[ = ] Bye"
