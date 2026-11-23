# Your App's Name
Concrete Needed for a Rectangular Slab
## Purpose
This is a small app that computes the concrete needed for a rectangular slab. Users will input the slab length and width in feet, thickness in inches, a waste factor as a percentage, and the price of concrete per cubic yard. The app will then show the volume in cubic yards (rounded up to the nearest quarter yard) and the total cost. The app will also show a diagram of the slab with its dimensions labeled.

## Inputs
W = Width of the concrete slab in feet entered with a slider.
L = Length of the concrete slab in feet entered with a slider.
T = Thickness of the concrete slab in inches entered with a slider.
Waste = Waste factor as a percentage entered using a number box. Range: 0-100
P = Price of concrete per cubic yard entered in dollars per cubic yard using a number box.

## Calculations
W = Width of the concrete slab in feet
L = Length of the concrete slab in feet
T = Thickness of the concrete slab in inches
Waste = Waste factor as a percentage
P = Price of concrete per cubic yard
Cost = (W*L*(T/12))*(1+W)*P


## Outputs
Cost as a number in dollars
3-D diagram of a slab with length L, width
What the app shows: numbers (with units), tables, plots, diagrams,
colors, animations.

## Look and feel
How the app looks and is laid out, what it shows when it first opens,
and how it works on a phone.

## Validation
At least one test case you have worked by hand: the exact inputs,
and the outputs the app must produce.

## Out of scope
Things the app will NOT do, so the agent doesn't add them.