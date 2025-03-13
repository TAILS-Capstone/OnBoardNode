#!/bin/bash
# Usage: ./split_into_720p.sh input_video.mp4

# Check if ffprobe and ffmpeg are installed
if ! command -v ffprobe &> /dev/null || ! command -v ffmpeg &> /dev/null; then
  echo "ffprobe and/or ffmpeg not found. Please install ffmpeg."
  exit 1
fi

if [ $# -ne 1 ]; then
  echo "Usage: $0 input_video.mp4"
  exit 1
fi

INPUT="$1"

# Get video resolution in format WIDTHxHEIGHT (e.g., 3840x2160)
resolution=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$INPUT")
width=$(echo "$resolution" | cut -d'x' -f1)
height=$(echo "$resolution" | cut -d'x' -f2)

echo "Input video resolution: ${width}x${height}"

# Define target tile dimensions (720p)
target_width=1280
target_height=720

# Verify that the width and height are multiples of the target dimensions
if (( width % target_width != 0 )); then
  echo "Warning: Width ($width) is not a multiple of $target_width."
  exit 1
fi

if (( height % target_height != 0 )); then
  echo "Warning: Height ($height) is not a multiple of $target_height."
  exit 1
fi

# Calculate number of columns and rows
cols=$(( width / target_width ))
rows=$(( height / target_height ))
total_tiles=$(( rows * cols ))

echo "Video will be split into $rows rows and $cols columns ($total_tiles tiles of 720p each)."

# Create output directory based on the input file name
filename=$(basename -- "$INPUT")
filename="${filename%.*}"
output_dir="${filename}_split"
mkdir -p "$output_dir"

# Loop through each tile and extract using the crop filter
tile=1
for (( r=0; r<rows; r++ )); do
  for (( c=0; c<cols; c++ )); do
    x_offset=$(( c * target_width ))
    y_offset=$(( r * target_height ))
    output="${output_dir}/tile_${tile}.mp4"
    echo "Creating tile $tile: crop=${target_width}x${target_height} at offset (${x_offset},${y_offset}) -> $output"
    ffmpeg -i "$INPUT" -filter:v "crop=${target_width}:${target_height}:${x_offset}:${y_offset}" -c:a copy "$output"
    tile=$(( tile + 1 ))
  done
done
