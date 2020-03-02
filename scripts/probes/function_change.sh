#!/bin/bash

if [ "$1" == "-h" ]; then
    echo "Usage: 'basename $0' [old_file] [new_file] [function_name]"
    exit 0
fi

extension="${1##*.}"

if [ "$extension" == "py" ]; then
    targeter="scripts/target_finders/python_ast.py"
    old_target=$(python $targeter $1 $3 | grep ':')
    new_target=$(python $targeter $2 $3 | grep ':')
fi

old_target_start=$(echo $old_target | cut -d ':' -f 1)
old_target_end=$(echo $old_target | cut -d ' ' -f 2 | cut -d ':' -f 1)
new_target_start=$(echo $new_target | cut -d ':' -f 1)
new_target_end=$(echo $new_target | cut -d ' ' -f 2 | cut -d ':' -f 1)

sed -n -e "$old_target_start,$old_target_end p" -e "$old_target_end q" $1 > old_function.txt
sed -n -e "$new_target_start,$new_target_end p" -e "$new_target_end q" $2 > new_function.txt

cmp --silent old_function.txt new_function.txt && echo 'False' ||  echo 'True'

rm old_function.txt && rm new_function.txt
