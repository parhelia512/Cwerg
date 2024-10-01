(module [] :

@pub (defrec TimeSpec :
    (field sec uint)
    (field nano_sec uint))


@pub @extern @cdecl (fun nanosleep [(param req (ptr TimeSpec)) (param rem (ptr! TimeSpec))] s32 :)


@pub @extern @cdecl (fun write [
        (param fd s32)
        (param s (ptr u8))
        (param size uint)] sint :)


@pub @extern @cdecl (fun read [
        (param fd s32)
        (param s (ptr! u8))
        (param size uint)] sint :)


@pub (@wrapped type Error s32)


@pub (@wrapped type FD s32)


@pub (global Stdin auto (wrap_as 0 FD))


@pub (global Stdout auto (wrap_as 1 FD))


@pub (global Stderr auto (wrap_as 2 FD))


@pub (fun FileWrite [(param fd FD) (param buffer (span u8))] (union [uint Error]) :
    (let res auto (write [(unwrap fd) (front buffer) (len buffer)]))
    (if (< res 0) :
        (return (wrap_as (as res s32) Error))
     :
        (return (as res uint))))


@pub (fun FileRead [(param fd FD) (param buffer (span! u8))] (union [uint Error]) :
    (let res auto (read [(unwrap fd) (front! buffer) (len buffer)]))
    (if (< res 0) :
        (return (wrap_as (as res s32) Error))
     :
        (return (as res uint))))


@pub (fun TimeNanoSleep [(param req (ptr TimeSpec)) (param rem (ptr! TimeSpec))] Error :
    (let res auto (nanosleep [req rem]))
    (return (wrap_as res Error)))
)

