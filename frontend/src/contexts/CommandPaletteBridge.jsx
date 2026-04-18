import { createContext, useContext } from 'react';

export const CommandPaletteBridgeContext = createContext({
  openPalette: () => {},
});

export function useOpenCommandPalette() {
  return useContext(CommandPaletteBridgeContext);
}
