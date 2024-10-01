@doc """canonical huffman tree decoder

https://datatracker.ietf.org/doc/html/rfc1951 Section 3.2
https://en.wikipedia.org/wiki/Canonical_Huffman_code


Usage:

Assumptions:
* encoded was as set symbols numbered 0-MAX_SYMBOLS
* for each symbol the width of the associated huffman code was recorded in a length slice
* unused symbols have a widths of 0
* we do not need to know the actual code for a symbol because we use canonical codes
"""
(module [] :
(import bitstream)


@pub (global BAD_SYMBOL u16 0xffff)


@pub (global BAD_TREE_ENCODING u16 0xffff)


(global MAX_SYMBOLS uint 0xff00)


@doc """Decode the next symbol from a bitstream

This function has two failure modes:
* the bitstream may run out of bits
  This must be checked by the caller
* the retrieved bits are out of range
  This will result in BAD_SYMBOL to be returned

  counts[i] contains the number of huffman code of 2^i
  Note counts[0] is not used
"""
@pub (fun NextSymbol [
        (param bs (ptr! bitstream::Stream32))
        (param counts (span u16))
        (param symbols (span u16))] u16 :
    (let! offset u32 0)
    (let! base u32 0)
    (for level 1 (len counts) 1 :
        (<<= offset 1)
        (+= offset (bitstream::Stream32GetBits [bs 1]))
        (let count u32 (as (at counts level) u32))
        (if (< offset count) :
            (+= base offset)
            (return (at symbols base))
         :)
        (+= base count)
        (-= offset count))
    (return BAD_SYMBOL))


@doc """Check that symbol count at a level can be encoded

"""
(fun CountsAreFeasible [(param counts (span u16))] bool :
    (let! available u16 2)
    (for level 1 (len counts) 1 :
        (let used auto (at counts level))
        (if (> used available) :
            (return false)
         :
            (= available (* (- available used) 2))))
    (return (== available 0)))


@doc """
Popoulates the counts and sybols from lengths

lengths[sym] contains the bitwidth of synbol sym.

Returns the number of elements in symbols populated which is usally
the number of nonzero entries in lengths.

If lengths has exactly one non-zero elemenmt an extra dummy element
will be inserted into symbols and 2 will be returned.

counts[width] contains the number of elments in lengths having value width.
Note counts[0] is always 0

"""
@pub (fun ComputeCountsAndSymbolsFromLengths [
        (param lengths (span u16))
        (param counts (span! u16))
        (param symbols (span! u16))] u16 :
    (if (> (len lengths) MAX_SYMBOLS) :
        (return BAD_TREE_ENCODING)
     :)
    (for level 0 (len counts) 1 :
        (= (at counts level) 0))
    (let! last u16 0)
    (for i 0 (len lengths) 1 :
        (let bits auto (at lengths i))
        (if (!= bits 0) :
            (= last (as i u16))
            (if (>= (as bits uint) (len counts)) :
                (return BAD_TREE_ENCODING)
             :)
            (+= (at counts bits) 1)
         :))
    (let! n u16 0)
    (for i 1 (len counts) 1 :
        (+= n (at counts i)))
    (cond :
        (case (== n 0) :
            @doc "this is odd but some tests rely on it"
            (return 0_u16))
        (case (== n 1) :
            @doc "also see below for more special handling"
            (if (!= (at counts 1) 1) :
                (return BAD_TREE_ENCODING)
             :))
        (case true :
            (if (! (CountsAreFeasible [counts])) :
                (return BAD_TREE_ENCODING)
             :)))
    @doc """accumulate counts to get offsets
    counts[i] := sum(0<= x <= i, counts[x])
    """
    (= n 0)
    (for i 1 (len counts) 1 :
        (+= n (at counts i))
        (= (at counts i) n))
    @doc "fill in symbols grouped by bit-width preserving ordered for same width symbols"
    (for i 0 (len symbols) 1 :
        (= (at symbols i) BAD_SYMBOL))
    (for i 0 (len lengths) 1 :
        (let bits auto (at lengths i))
        (if (!= bits 0) :
            (let offset auto (at counts (- bits 1)))
            (= (at symbols offset) (as i u16))
            (+= (at counts (- bits 1)) 1)
         :))
    @doc """de-accumulate to get back original count

    at this point we have: counts_now[i] == sum(0<= x <= i + 1, counts_orig[x])
    we compute:  counts_orig[i] := counts_now[i - 1] -   counts_now[i - 2]

    n0 is the original value of the element at index i-2
    n1 is the original value of the element at index i-1"""
    (let! n0 u16 0)
    (let! n1 u16 0)
    (for i 0 (len counts) 1 :
        (let d auto (- n1 n0))
        (= n0 n1)
        (= n1 (at counts i))
        (= (at counts i) d))
    @doc "weird case"
    (if (== n 1) :
        (= (at counts 1) 2)
        (= (at symbols 1) BAD_SYMBOL)
        (+= n 1)
     :)
    (return n))
)
