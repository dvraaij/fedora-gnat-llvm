# Package `gnat-llvm`

[![Copr build status](https://copr.fedorainfracloud.org/coprs/dvraaij/ada/package/gnat-llvm/status_image/last_build.png)](https://copr.fedorainfracloud.org/coprs/dvraaij/ada/package/gnat-llvm/)

Experimental package based on the upstream repository found [here](https://github.com/AdaCore/gnat-llvm).

## Known issues

- Only static RTS libaries are provided at this point.

- The GNAT-LLVM runtime systems (RTS) are not yet automatically detected by `gprconfig` so they must be provided explicitly for each build.

  To use the native RTS:
  ```shell
  $ llvm-gnatmake --RTS=/usr/lib64/libgnat-llvm/rts-native main.adb
  ```

  To use the zero-footprint RTS:
  ```shell
  $ llvm-gnatmake --RTS=/usr/lib64/libgnat-llvm/rts-zfp main.adb
  ```