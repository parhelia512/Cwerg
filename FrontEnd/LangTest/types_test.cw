(module [] :

(@wrapped type t1 s32)


(@wrapped type t2 void)


(@wrapped type t3 void)


@pub (defrec type_rec :
    @doc """this is a comment with \" with quotes \t"""
    (field s1 s32)
    (field s2 s32)
    (field s3 s32)
    (field s4 s32)
    (field b1 bool)
    (field u1 u64)
    (field u2 u64))


@pub (defrec linked_list :
    @doc """this is a comment with \" with quotes \t"""
    (field s1 (union [void (ptr linked_list)])))


@pub (enum type_enum S32 :
    @doc """this is a comment with \" with quotes \t"""
    (entry s1)
    (entry s2)
    (entry s3)
    (entry s4))


(type type_array (array 3 bool))


(type type_slice (span type_rec))


(type type_ptr (ptr! s32))


@pub (type type_union (union [s32 void type_ptr]))


@pub (type type_union2 (union [s32 void (union [type_union u8])]))


(type type_fun (sig [
        (param a bool)
        (param b bool)
        (param c s32)] s32))


(fun funx [(param a type_union)] s32 :
    (return (narrow_as a (union_delta type_union (union [void type_ptr])))))

@doc "just a compilation test"
(fun main [(param argc s32) (param argv (ptr (ptr u8)))] s32 :
   (return 0))
)