#!/bin/bash

if [ "$1" == "-h" ]; then
    echo "Usage: 'basename $0' [old_file] [new_file] [target] [targetType]"
    exit 0
fi

old_file=$1
new_file=$2

if [ -z "$4" || "$4" == "file" ]; then
        cmp --silent old_code.txt new_code.txt && echo 'False' || echo 'True'
        exit 0
    elif [ "$4" == "function" ]; then
        target="func($3)"
    elif [ "$4" == "class" ]; then
        target="class($3)"
    else
        exit 1
fi

extension="${1##*.}"

if [ "$extension" == "py" ]; then
    targeter="scripts/target_finders/python_ast.py"
    old_target=$(python3 $targeter $old_file $target | grep ':')
    new_target=$(python3 $targeter $new_file $target | grep ':')
fi

# Should probably change target output format so janky commands like this aren't necessary...
old_target_start=$(echo $old_target | cut -d ':' -f 1)
old_target_end=$(echo $old_target | cut -d ' ' -f 2 | cut -d ':' -f 1)
new_target_start=$(echo $new_target | cut -d ':' -f 1)
new_target_end=$(echo $new_target | cut -d ' ' -f 2 | cut -d ':' -f 1)

sed -n -e "$old_target_start,$old_target_end p" -e "$old_target_end q" $1 > old_code.txt
sed -n -e "$new_target_start,$new_target_end p" -e "$new_target_end q" $2 > new_code.txt

cmp --silent old_code.txt new_code.txt && echo 'False' || echo 'True'

rm old_code.txt && rm new_code.txt
