@doc "Linked List Example"
(module [] :
(import test)

(import fmt)


(@wrapped type NoneType void)


@pub (global None auto (wrap_as void_val NoneType))


@pub (defrec LinkedListNode :
    (field next (union [NoneType (ptr! LinkedListNode)]))
    (field payload u32))


(type MaybeNode (union [NoneType (ptr! LinkedListNode)]))


(fun SumPayload [(param root MaybeNode)] u32 :
    (let! sum u32 0)
    (let! node MaybeNode root)
    (while true :
        (trylet x (ptr! LinkedListNode) node _ :
            (break))
        (+= sum (^. x payload))
        (= node (^. x next)))
    (return sum))


(global N uint 100)


(global! NodePool auto (vec_val N LinkedListNode))


@doc "currently (* N 24) but should be (* N 16) on 64 bit system with union optimization"
(static_assert (== (size_of (type_of NodePool)) (* (* N 3) (size_of (ptr! LinkedListNode)))))


(fun DumpNode [(param i u32)] void :
    (fmt::print# i " " (. (at NodePool i) payload) " " (union_tag (. (at NodePool i) next)))
    (if (is (. (at NodePool i) next) NoneType) :
        (fmt::print# " next: NULL\n")
     :
        (fmt::print# " next: " (unsafe_as (narrow_as (. (at NodePool i) next) (ptr! LinkedListNode)) (ptr void)) "\n")))


(fun main [(param argc s32) (param argv (ptr (ptr u8)))] s32 :
    (fmt::print# "start: " (unsafe_as (front NodePool) (ptr void)) "\n")
    (for i 0 N 1 :
        (= (. (at NodePool i) payload) (as i u32))
        (if (== i (- N 1)) :
            (= (. (at NodePool i) next) None)
         :
            (= (. (at NodePool i) next) (&! (at NodePool (+ i 1))))))
    @doc """
    (for i 0 N 1 :
       (do (DumpNode [i])))
    """
    (test::AssertEq# (SumPayload [(front! NodePool)]) 4950_u32)
    (test::Success#)
    (return 0))
)
