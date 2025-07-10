"""
* Given an AtBatResult + context (runs scored list, play code, batter, pitcher), 
  returns a list of StatDelta instances for every stat (ab, h, r, rbi, sb, cs, po, a, e, etc.).
* Houses your “desired_order,” “auto-rbi codes,” and field mappings.
"""