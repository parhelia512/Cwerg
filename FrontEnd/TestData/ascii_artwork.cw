@doc """
* https://github.com/cmatsuoka/asciiquarium
* https://robobunny.com/projects/asciiquarium/
* Artwork by Joan Stark: http://www.geocities.com/SoHo/7373/ (see archive.org copy)"""
(module [] :
(import aanim ./ascii_anim)


@doc """Color codes and xterm rgb values:
k  black    0,0,0
r  red      205,0, 0
g  green    0,205,0
y  yellow   205,205,0
b  blue     0,0,238
m  magenta  205,0,205
c  cyan     0,205,205
w  white    229,229,229
t  translucent


Fish body parts:
1: body
2: dorsal fin
3: flippers
4: eye
5: mouth
6: tailfin
7: gills
"""
@pub (global RandomColor auto "RcRyBgM")


(global CastleSprites auto (vec_val 1 aanim::Sprite [(rec_val aanim::Sprite [
                r"""
                T~~
                |
               /^\
              /   \
  _   _   _  /     \  _   _   _
 [ ]_[ ]_[ ]/ _   _ \[ ]_[ ]_[ ]
 |_=__-_ =_|_[ ]_[ ]_|_=-___-__|
  | _- =  | =_ = _    |= _=   |
  |= -[]  |- = _ =    |_-=_[] |
  | =_    |= - ___    | =_ =  |
  |=  []- |-  /| |\   |=_ =[] |
  |- =_   | =| | | |  |- = -  |
  |_______|__|_|_|_|__|_______|
"""
                r"""
                 RR

               yyy
              y   y
             y     y
            y       y



               yyy
              yy yy
             y y y y
             yyyyyyy
"""])]))


@pub (global Castle auto (rec_val aanim::Object ["castle" CastleSprites 'B' (field_val 22 def_depth)]))


(global SwanLSprites auto (vec_val 1 aanim::Sprite [(rec_val aanim::Sprite [
                r"""
 ___
/,_ \    _,
|/ )/   / |
  //  _/  |
 / ( /   _)
/   `   _/)
\  ~=-   /
"""
                r"""

 g
yy
"""])]))


@pub (global SwanL auto (rec_val aanim::Object ["swan_l" SwanLSprites 'W' (field_val 3 def_depth) (field_val -1.0_r32 def_x_speed)]))


(global SwanRSprites auto (vec_val 1 aanim::Sprite [(rec_val aanim::Sprite [
                r"""
        ___
 ,_    / _,\
 | \   \( \|
 |  \_  \\\
 (_   \_) \
 (\_   `   \
  \   -=~  /
"""
                r"""

          g
          yy
"""])]))


@pub (global SwanR auto (rec_val aanim::Object ["swan_r" SwanRSprites 'W' (field_val 3 def_depth) (field_val -1.0_r32 def_x_speed)]))


(global DucksRSprites auto (vec_val 3 aanim::Sprite [
        (rec_val aanim::Sprite [
                r"""
      _??????????_??????????_
,____(')=??,____(')=??,____(')<
 \~~= ')????\~~= ')????\~~= ')
"""
                r"""
      g          g          g
wwwwwgcgy  wwwwwgcgy  wwwwwgcgy
 wwww Ww    wwww Ww    wwww Ww
"""])
        (rec_val aanim::Sprite [
                r"""
      _??????????_??????????_
,____(')=??,____(')<??,____(')=
 \~~= ')????\~~= ')????\~~= ')
"""
                r"""
      g          g          g
wwwwwgcgy  wwwwwgcgy  wwwwwgcgy
 wwww Ww    wwww Ww    wwww Ww
"""])
        (rec_val aanim::Sprite [
                r"""
      _??????????_??????????_
,____(')<??,____(')=??,____(')=
 \~~= ')????\~~= ')????\~~= ')
"""
                r"""
      g          g          g
wwwwwgcgy  wwwwwgcgy  wwwwwgcgy
 wwww Ww    wwww Ww    wwww Ww
"""])]))


@pub (global DuckR auto (rec_val aanim::Object ["duck_r1" DucksRSprites 'W' (field_val 3 def_depth) (field_val '?' transparent_char) (field_val 1.0_r32 def_x_speed)]))


(global DolphinRSprites auto (vec_val 2 aanim::Sprite [(rec_val aanim::Sprite [
                r"""
        ,
      __)\_
(\_.-'    a`-.
(/~~````(/~^^`
"""
                r"""


          W
"""]) (rec_val aanim::Sprite [
                r"""
        ,
(\__  __)\_
(/~.''    a`-.
    ````\)~^^`
"""
                r"""


          W
"""])]))


@pub (global DolphinR auto (rec_val aanim::Object ["dolphin_r" DolphinRSprites 'b' (field_val 3 def_depth) (field_val 1.0_r32 def_x_speed)]))


(global DolphinLSprites auto (vec_val 2 aanim::Sprite [(rec_val aanim::Sprite [
                r"""
     ,
   _/(__
.-'a    `-._/)
'^^~\)''''~~\)
"""
                r"""


   W
"""]) (rec_val aanim::Sprite [
                r"""
     ,
   _/(__  __/)
.-'a    ``.~\)
'^^~(/''''
"""
                r"""


   W
"""])]))


@pub (global DolphinL auto (rec_val aanim::Object ["dolphin_r" DolphinLSprites 'b' (field_val 3 def_depth) (field_val -1.0_r32 def_x_speed)]))


(global BigFishRSprites auto (vec_val 1 aanim::Sprite [(rec_val aanim::Sprite [
                r"""
 ______
`""-.  `````-----.....__
     `.  .      .       `-.
       :     .     .       `.
 ,     :   .    .          _ :
: `.   :                  (@) `._
 `. `..'     .     =`-.       .__)
   ;     .        =  ~  :     .-"
 .' .'`.   .    .  =.-'  `._ .'
: .'   :               .   .'
 '   .'  .    .     .   .-'
   .'____....----''.'=.'
   ""             .'.'
               ''"'`
"""
                r"""
 111111
11111  11111111111111111
     11  2      2       111
       1     2     2       11
 1     1   2    2          1 1
1 11   1                  1W1 111
 11 1111     2     1111       1111
   1     2        1  1  1     111
 11 1111   2    2  1111  111 11
1 11   1               2   11
 1   11  2    2     2   111
   111111111111111111111
   11             1111
               11111
"""])]))


@pub (global BigFishR auto (rec_val aanim::Object ["bigfish_r" BigFishRSprites 'Y' (field_val 2 def_depth) (field_val 3.0_r32 def_x_speed)]))


(global BigFishLSprites auto (vec_val 1 aanim::Sprite [(rec_val aanim::Sprite [
                r"""
                           ______
          __.....-----'''''  .-""'
       .-'       .      .  .'
     .'       .     .     :
    : _          .    .   :     ,
 _.' (@)                  :   .' :
(__.       .-'=     .     `..' .'
 "-.     :  ~  =        .     ;
   `. _.'  `-.=  .    .   .'`. `.
     `.   .               :   `. :
       `-.   .     .    .  `.   `
          `.=`.``----....____`.
            `.`.             ""
              '`"``
"""
                r"""
                           111111
          11111111111111111  11111
       111       2      2  11
     11       2     2     1
    1 1          2    2   1     1
 111 1W1                  1   11 1
1111       1111     2     1111 11
 111     1  1  1        2     1
   11 111  1111  2    2   1111 11
     11   2               1   11 1
       111   2     2    2  11   1
          111111111111111111111
            1111             11
              11111
"""])]))


@pub (global BigFishL auto (rec_val aanim::Object ["bigfish_l" BigFishLSprites 'Y' (field_val 2 def_depth) (field_val 3.0_r32 def_x_speed)]))


(global MonsterRSprites auto (vec_val 4 aanim::Sprite [
        (rec_val aanim::Sprite [
                r"""
                                                          ____
            __??????????????????????????????????????????/   o  \
          /    \????????_?????????????????????_???????/     ____ >
  _??????|  __  |?????/   \????????_????????/   \????|     |
 | \?????|  ||  |????|     |?????/   \?????|     |???|     |
"""
                r"""

                                                            W



"""])
        (rec_val aanim::Sprite [
                r"""
                                                          ____
                                             __?????????/   o  \
             _?????????????????????_???????/    \?????/     ____ >
   _???????/   \????????_????????/   \????|  __  |???|     |
  | \?????|     |?????/   \?????|     |???|  ||  |???|     |
"""
                r"""

                                                            W



"""])
        (rec_val aanim::Sprite [
                r"""
                                                          ____
                                  __????????????????????/   o  \
 _??????????????????????_???????/    \????????_???????/     ____ >
| \??????????_????????/   \????|  __  |?????/   \????|     |
 \ \???????/   \?????|     |???|  ||  |????|     |???|     |
"""
                r"""

                                                            W



"""])
        (rec_val aanim::Sprite [
                r"""
                                                          ____
                       __???????????????????????????????/   o  \
  _??????????_???????/    \????????_??????????????????/     ____ >
 | \???????/   \????|  __  |?????/   \????????_??????|     |
  \ \?????|     |???|  ||  |????|     |?????/   \????|     |
"""
                r"""

                                                            W



"""])]))


@pub (global MonsterR auto (rec_val aanim::Object [
        "monster_r"
        MonsterRSprites
        'G'
        (field_val 5 def_depth)
        (field_val '?' transparent_char)
        (field_val 2.0_r32 def_x_speed)]))


(global ShipRSprites auto (vec_val 1 aanim::Sprite [(rec_val aanim::Sprite [
                r"""
     |    |    |
    )_)  )_)  )_)
   )___))___))___)\
  )____)____)_____)\\\
_____|____|____|____\\\\\__
\                   /
"""
                r"""
     y    y    y

                  w
                   ww
yyyyyyyyyyyyyyyyyyyywwwyy
y                   y
"""])]))


@pub (global ShipR auto (rec_val aanim::Object ["ship_r" ShipRSprites 'W' (field_val 7 def_depth) (field_val 1.0_r32 def_x_speed)]))


(global SharkRSprites auto (vec_val 1 aanim::Sprite [(rec_val aanim::Sprite [
                r"""
                              __
                             ( `\
  ,??????????????????????????)   `\
;' `.????????????????????????(     `\__
 ;   `.?????????????__..---''          `~~~~-._
  `.   `.____...--''                       (b  `--._
    >                     _.-'      .((      ._     )
  .`.-`--...__         .-'     -.___.....-(|/|/|/|/'
 ;.'?????????`. ...----`.___.',,,_______......---'
 '???????????'-'
"""
                r"""





                                           cR

                                          cWWWWWWWW


"""])]))


@pub (global SharkR auto (rec_val aanim::Object ["ship_r" SharkRSprites 'C' (field_val 2 def_depth) (field_val '?' transparent_char) (field_val 2.0_r32 def_x_speed)]))


(global Fish1RSprites auto (vec_val 1 aanim::Sprite [(rec_val aanim::Sprite [
                r"""
       \
     ...\..,
\  /'       \
 >=     (  ' >
/  \      / /
    `"'"'/''
"""
                r"""
       2
     1112111
6  11       1
 66     7  4 5
6  1      3 1
    11111311
"""])]))


@pub (global Fish1R auto (rec_val aanim::Object ["fish1_r" Fish1RSprites 'C' (field_val 2 def_depth)]))


@pub (fun UpdateState [
        (param s (ptr! aanim::ObjectState))
        (param t r32)
        (param dt r32)] void :
    (= (^. s x_pos) (+ (^. s x_pos) (* (^. s x_speed) dt)))
    (= (^. s y_pos) (+ (^. s y_pos) (* (^. s y_speed) dt)))
    (+= (^. s frame) 1)
    (if (>= (^. s frame) (len (^. (^. s obj) sprites))) :
        (= (^. s frame) 0)
     :))
)

