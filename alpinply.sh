#!/bin/sh
## Author: lostsh
##
## Script to apply .cube LUT file to a picture
##

TEMP_DIR="/tmp"
FILTER_NEUTRAL="id_level.png"
FILTER_CUBE="halt_lut.png"

echo -e "\t[+] Apply LUT file to picture\n"

print_usage (){
    echo -e "\t[?] Usage:\t$0 -c lut_file.cube -p picture.jpg"
    echo -e "\t\t\t-o output_file.jpg"
    echo -e "\t\t\tls files.jpg | $0 lut_file.cube"
    if [ $# -gt 0 ]; then
        echo -e "\t[!] $1" >&2
        exit;
    fi
}

# Fuction take a .cube lut file
# Convert it to a png file using ffmpeg and convert
# $1: input .cube file
convert_lut_to_png (){
    magick hald:8 "${TEMP_DIR}/${FILTER_NEUTRAL}" \
    && ffmpeg -nostdin -y -i "${TEMP_DIR}/${FILTER_NEUTRAL}" -vf "lut3d=$1" "${TEMP_DIR}/${FILTER_CUBE}" 2>/dev/null
}

# Apply png lut filter to jpg picture
# $1: input jpg picture
# $2: output file name
apply_filter (){
    magick "$1" "${TEMP_DIR}/${FILTER_CUBE}" -hald-clut "$2"
}

[ $# -lt 1 ] && print_usage "Missing LUT (.cube) file"
echo -e "\t[ = ] Run"


#	##==============##
#	## Main section ##
#	##______________##
if [ $# -lt 2 ]; then
    convert_lut_to_png "$1"
    shift
    while read -r input_pic; do
        apply_filter $input_pic "n_$input_pic"
        [[ $? == 0 ]] && echo -e "\t[ ^ ] $input_pic\t OK" || echo -e "\t[ v ] $input_pic\t KO"
    done
fi

lut_cube_file=""
picture_file=""
out_name=""
# switch mode from signle file to list
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
            out_name="$2"
            shift
        ;;
        *)
            help "Wrong argument $1"
        ;;
    esac
    shift #next argument
done

# Execute single file script mode
[[ "$lut_cube_file" != "" ]] \
&& [[ "$picture_file" != "" ]] \
&& [[ "$out_name" != "" ]] \
&& convert_lut_to_png $lut_cube_file \
&& apply_filter $picture_file $out_name \
&& echo -e "\t[ ^ ] OK"

# cleaup temp files
[ -f "${TEMP_DIR}/${FILTER_NEUTRAL}" ] && rm -f "${TEMP_DIR}/${FILTER_NEUTRAL}"
[ -f "${TEMP_DIR}/${FILTER_CUBE}" ] && rm -f "${TEMP_DIR}/${FILTER_CUBE}"

echo -e "\t[ = ] Bye"
