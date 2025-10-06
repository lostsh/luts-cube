#!/bin/bash

echo -e "\t[+] Apply LUT file to picture\n"

if [ $# -lt 2 ]; then
    echo -e "\t[ ! ] Missing args\n\t\tInput : pic, .cube file\n"
fi
echo -e "\t[ = ] Run"

convert hald:8 id_level.png \
&& ffmpeg -y -i id_level.png -vf "lut3d=$1" halt_lut.png 2>/dev/null \
&& convert $2 halt_lut.png -hald-clut out.jpg

[[ $? == 0 ]] && echo -e "\t[ ^ ] OK" || echo -e "\t[ v ] KO"

# cleaup temp files
rm -f id_level.png halt_lut.png
