#!/bin/sh

echo -ne "=> [${@}]\n"
echo "Home var: $HOME"
echo "ls home: "
ls -a ~

echo "Input file"
echo "$1: $2"
ls -alth $2
echo "Input Cube"
echo "$3: $4"
ls -alth $4
echo "Output"
echo "$5: $6"
ls -alth $6
