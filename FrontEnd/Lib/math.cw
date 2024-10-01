@doc "math module"
(module [] :

@doc "e"
@pub (global E r64 2.718281828459045235360287471352662498)


@doc "log_2 e"
@pub (global LOG2_E r64 1.442695040888963407359924681001892137)


@doc "log_10(e)"
@pub (global LOG10_E r64 0.434294481903251827651128918916605082)


@doc "log_e(2)"
@pub (global LN_2 r64 0.693147180559945309417232121458176568)


@doc "log_e(10)"
@pub (global LN_10 r64 2.302585092994045684017991454684364208)


@doc "pi"
@pub (global PI r64 3.141592653589793238462643383279502884)


@doc "pi / 2"
@pub (global PI_2 r64 1.570796326794896619231321691639751442)


@doc "pi / 4"
@pub (global PI_4 r64 0.785398163397448309615660845819875721)


@doc "1 / pi"
@pub (global ONE_PI r64 0.318309886183790671537767526745028724)


@doc "2 / pi"
@pub (global TWO_PI r64 0.636619772367581343075535053490057448)


@doc "2 / sqrt(pi)"
@pub (global TWO__SQRT_PI r64 1.128379167095512573896158903121545172)


@doc "sqrt(2)"
@pub (global SQRT_2 r64 1.414213562373095048801688724209698079)


@doc "1 / sqrt(2)"
@pub (global ONE_SQRT_2 r64 0.707106781186547524400844362104849039)


@doc "sqrt(3)"
@pub (global SQRT_3 r64 1.7320508075688772935274463415058723669428)


@doc "1 / sqrt(3)"
@pub (global ONE_SQRT_3 r64 0.5773502691896257645091487805019574556476)


@doc "Kahan's doubly compensated summation. Less accurate but fast"
(fun sum_kahan_compensated [(param summands (span r64))] r64 :
    (let! s r64 0.0)
    (let! c r64 0.0)
    (for i 0 (len summands) 1 :
        (let x auto (at summands i))
        (let y auto (- x c))
        (let t auto (+ s y))
        (= c (- (- t s) y))
        (= s t))
    (return s))


@pub (defrec SumCompensation :
    (field sum r64)
    (field compensation r64))


@doc "Priest's doubly compensated summation. Accurate but slow"
(fun sum_priest_compensated [(param summands (span r64))] SumCompensation :
    (let! s r64 0.0)
    (let! c r64 0.0)
    (for i 0 (len summands) 1 :
        (let x auto (at summands i))
        (let y auto (+ c x))
        (let u auto (- x (- y c)))
        (let t auto (+ y s))
        (let v auto (- y (- t s)))
        (let z auto (+ u v))
        (= s (+ t z))
        (= c (- z (- s t))))
    (return (rec_val SumCompensation [s c])))


(fun horner_sum [(param x r64) (param coeffs (span r64))] r64 :
    (let! s r64 0.0)
    (for i 0 (len coeffs) 1 :
        (let c auto (at coeffs i))
        (= s (+ (* s x) c)))
    (return s))
)

