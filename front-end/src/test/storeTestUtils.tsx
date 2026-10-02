import { configureStore, EnhancedStore } from "@reduxjs/toolkit";
import { TypedUseSelectorHook, useDispatch, useSelector } from "react-redux";
import { rootReducer } from "../stores/rootReducer";
import { AppDispatch, RootState } from "../stores/store";

// Create a minimal store for testing that includes all reducers
export const createTestStore = (preloadedState?: Partial<RootState>) => {
  return configureStore({
    reducer: rootReducer,
    preloadedState: preloadedState as any,
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware({
        serializableCheck: false,
        immutableCheck: false,
      }),
  });
};

// Type-safe hooks for testing
export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;

// Wrapper component for testing connected components
import { ReactNode } from "react";
import { Provider } from "react-redux";

interface TestWrapperProps {
  children: ReactNode;
  store?: EnhancedStore;
}

export const TestWrapper: React.FC<TestWrapperProps> = ({ 
  children, 
  store = createTestStore() 
}) => {
  return (
    <Provider store={store}>
      {children}
    </Provider>
  );
};

// Render function with all providers
import { render, RenderOptions } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";

const AllTheProviders: React.FC<{ children: ReactNode; store?: EnhancedStore }> = ({ 
  children, 
  store = createTestStore() 
}) => {
  return (
    <Provider store={store}>
      <MantineProvider>
        {children}
      </MantineProvider>
    </Provider>
  );
};

export const renderWithStore = (
  ui: ReactNode,
  options?: Omit<RenderOptions, "wrapper"> & { store?: EnhancedStore }
) => {
  const { store: testStore, ...renderOptions } = options || {};
  const Wrapper = ({ children }: { children: ReactNode }) => (
    <AllTheProviders store={testStore}>{children}</AllTheProviders>
  );
  
  return render(ui, { wrapper: Wrapper, ...renderOptions });
};

// Re-export for convenience
export * from "@testing-library/react";
export { fireEvent, waitFor, screen } from "@testing-library/react";