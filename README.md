# Apply lut file in .cube format

## Local
```bash
./alply.sh -c luts/luts/bw_red_filter_25.cube -p in.JPG -o out.jpg
```
## Container

# luts
`lutgen.py` is parametric. Every look is composable ops (s_curve, lift_gamma_gain, split_tone, channel_curve, vibrance, temperature). 

```bash
LUT_SIZE=65 python3 lutgen.py out/ #for 65³.
```

`preview.py` re-parses each .cube with an independent reader and applies it by trilinear interpolation.

# Help

Main command to apply lut in cube format: 

```bash
ffmpeg -y -i Input.JPG -vf lut3d=lut_file.cube Output.jpgj
```

To test for all luts
```bash
for f in $(ls luts/luts/*.cube); do
    ./alply.sh -c $f -p in.JPG -o "out_$(basename $f).jpg";
done
```