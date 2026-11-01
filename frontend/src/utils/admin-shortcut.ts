// A shortcut to the sign-in screen only. Server-side roles still control access.
export function createLogoPressSequence(maxGapMs = 1000) {
  let count = 0;
  let lastPress: number | null = null;
  const reset = () => { count = 0; lastPress = null; };
  return {
    reset,
    press(now: number) {
      if (lastPress === null || now - lastPress > maxGapMs || now < lastPress) count = 0;
      lastPress = now;
      count += 1;
      if (count !== 7) return false;
      reset();
      return true;
    },
  };
}
