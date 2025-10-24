# Understanding Fortran Format Specifications (The "Weird" Spacing)

## Why Some Fields Have Spaces and Others Don't

### The Fortran Format String:
```fortran
format (a1,i5,1x,i2,1x,i2,1x,i2,1x,i2,1x,f5.2,1x,
     & f8.4,1x,f9.4,1x,f7.2,f6.2,f6.2,f6.2,f6.2,1x,i10)
```

### The Key: Look for `1x`

**`1x` = explicit space character**

- If you see `1x` between format codes → **there IS a space**
- If you DON'T see `1x` → **fields run together (NO space)**

### Field-by-Field Breakdown:

```
#     i5    1x    i2    1x    i2    1x    i2    1x    i2    1x    f5.2   1x
  1      2      3      4      5      6      7      8      9     10     11     12

f8.4   1x    f9.4   1x    f7.2  f6.2  f6.2  f6.2  f6.2   1x    i10
 13     14     15     16     17    18    19    20    21     22     23
```

**WITH space (1x):**
- `#` → Year (space)
- Year → Month (space)
- Month → Day (space)
- Day → Hour (space)
- Hour → Minute (space)
- Minute → Second (space)
- Second → Latitude (space)
- Latitude → Longitude (space)
- Longitude → Depth (space)
- RMS → EventID (space)

**WITHOUT space (no 1x):**
- Depth → Magnitude → HErr → ZErr → RMS (all run together!)

### Visual Example:

```
# 2020  3  9 10 51 18.61  40.4657 -124.4777   29.78  0.00  0.00  0.00  0.00     100000
^     ^  ^  ^  ^  ^     ^        ^         ^       ↑no space between these↑      ^
│     │  │  │  │  │     │        │         │                                    │
│     │  │  │  │  │     │        │         └─ f7.2 (depth)                      │
│     │  │  │  │  │     │        └─ f9.4 (longitude)                            │
│     │  │  │  │  │     └─ f8.4 (latitude)                                      │
│     │  │  │  │  └─ f5.2 (seconds)                                             │
│     │  │  │  └─ i2 (minute)                                                   │
│     │  │  └─ i2 (hour)                                                        │
│     │  └─ i2 (day)                                                            │
│     └─ i2 (month)                                                             │
└─ i5 (year with leading space)                                                 │
                                                                                 └─ i10 (event ID)

Look at depth→mag→eh→ez→rms:
   29.78  0.00  0.00  0.00  0.00
   ↑    ↑    ↑    ↑    ↑
   f7.2 f6.2 f6.2 f6.2 f6.2  ← No 1x between them!
```

### Why This Design?

**Historical reasons + efficiency:**

1. **Save space**: Old punch cards had limited columns (80 chars)
2. **Fixed-width fields don't need separators**: If depth is always 7 chars (f7.2), mag is always 6 chars (f6.2), you don't need a space to tell where one ends and the next begins
3. **Human readability**: They added spaces (`1x`) between "logical groups" like date/time components

### Python Translation:

When we write this in Python, we need to match it exactly:

```python
# WITH spaces (1x in Fortran):
f"#{yr:5d} {mo:2d} {dy:2d} ..."
       ↑    ↑    ↑  ← spaces here

# WITHOUT spaces (no 1x in Fortran):
f"{depth:7.2f}{mag:6.2f}{eh:6.2f}{ez:6.2f}{rms:6.2f}"
             ↑       ↑      ↑      ↑  ← NO spaces!
```

### The Actual Line in Our Code:

```python
f"#{yr:5d} {mo:2d} {dy:2d} {hr:2d} {mn:2d} {sc:5.2f} "
f"{lat:8.4f} {lon:9.4f} {depth:7.2f}{mag:6.2f}{eh:6.2f}{ez:6.2f}{0.0:6.2f} {event_id:10d}\n"
                                    ↑                                      ↑
                                    └─ no space here                       └─ space here
```

## Pro Tips:

1. **Count the `1x`**: Each `1x` means add a space in Python f-string
2. **Fixed-width = reliable parsing**: Even with no spaces, Fortran knows "chars 44-50 = depth, chars 51-56 = mag"
3. **Free format (`read *`) is more forgiving**: But fixed format still matters for other tools
4. **When in doubt, copy the example**: The Calaveras.pha file is your template!

## Why Fortran Does This:

```fortran
! Old school way (1970s):
write(10, '(f7.2, f6.2)') depth, mag
! Outputs: "  29.78  0.00" (no separator needed)

! Modern way (easier to read):
write(10, '(f7.2, 1x, f6.2)') depth, mag
! Outputs: "  29.78   0.00" (with space)
```

The HypoDD format was designed in the 1990s-2000s, so it's a mix of old fixed-format style (no spaces between floats) and newer readable style (spaces between date/time components).

**Bottom line:** It's weird, but once you see the pattern, it makes sense! Just look for `1x` in the format string. 😊
