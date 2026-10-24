import { ChangeEventHandler, ReactNode, useCallback, useEffect, useRef } from "react";
import { useForm, FieldValues, PathValue, Path, UseFormRegisterReturn, Control } from "react-hook-form";
import { valibotResolver } from "@hookform/resolvers/valibot";
import { useLocation } from "react-router-dom";

export type RenderingHelpers<T extends FieldValues> = {
  hasFieldError(name: Path<T>): boolean;
  registerControl: RegisterControl<T>;
  getFieldError: (name: Path<T>) => string | null;
  setControlValue: (name: Path<T>, value: PathValue<T, Path<T>>, shouldDirty: boolean, triggerAll?: boolean) => void;
  control: Control<T, unknown, T>;
  getControlValue: (name: Path<T>) => PathValue<T, Path<T>>;
  getFieldChanged: (name: Path<T>) => boolean;
  trigger: (name?: Path<T>) => Promise<boolean>;
};

type RenderingContext<T extends FieldValues> = {
  helpers: RenderingHelpers<T>;
  title: string;
  userContext: unknown;
};

export type DynamicFieldConfig<T extends FieldValues> = {
  name: Path<T>;
  title: string;
  shouldRender?: (data: T) => boolean;
  render?: (context: RenderingContext<T>) => ReactNode;
  required?: boolean;
};

interface UseFormHandlerProps<T extends FieldValues> {
  isEdit: boolean;
  fields?: Array<DynamicFieldConfig<T>>;
  defaultRender?: (name: Path<T>, title: string, context: RenderingContext<T>) => ReactNode;
  initialData?: T;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  validationSchema: any;
  fetchDataAction: () => void;
  saveAction: (data: T) => void;
  cleanupAction: () => void;
  errorFormatter?: (message: string) => string;
  loading?: boolean;
  formKey: string;
  useLocationGuard?: boolean;
};

export type RegisterControlReturn<T> = Omit<UseFormRegisterReturn<Path<T>>, "onChange"> & {
  onChange: ChangeEventHandler<HTMLInputElement>;
  error: string;
};

export type RegisterControl<T> = (name: Path<T>) => RegisterControlReturn<T>;

export const useFormHandler = <T extends FieldValues>({
  isEdit,
  initialData,
  validationSchema,
  fetchDataAction,
  saveAction,
  cleanupAction,
  errorFormatter,
  loading,
  fields,
  defaultRender,
  formKey,
  useLocationGuard = true,
}: UseFormHandlerProps<T>) => {
  const {
    handleSubmit,
    setValue,
    trigger,
    register,
    reset,
    control,
    getFieldState,
    formState: { errors, isDirty, isValid, },
    getValues,
    setError,
  } = useForm<T>({
    resolver: valibotResolver(validationSchema),
    shouldUseNativeValidation: false,
    criteriaMode: 'all',
  });

  // eslint-disable-next-line react-hooks/rules-of-hooks
  const location = useLocationGuard ? useLocation() : { key: formKey };
  useEffect(() => {
    fetchDataAction();

    return () => {
      cleanupAction();
    };
  }, [location?.key]);

  const hasReset = useRef(false);
  useEffect(() => {
    const isReady = !loading && initialData && Object.keys(initialData).length > 0;

    if (isReady && !hasReset.current) {
      reset(initialData);
      if (isEdit) trigger();
      hasReset.current = true;
    }
  }, [loading, initialData, isEdit, reset, trigger]);

  const handleReset = (): void => {
    reset(initialData);
    trigger();
  };

  const setControlValue = useCallback((
    name: Path<T>,
    value: PathValue<T, Path<T>>,
    shouldDirty: boolean = true,
    triggerAll: boolean = false,
  ): void => {
    setValue(name, value, { shouldDirty: shouldDirty });
    if (triggerAll) {
      trigger();
    } else {
      trigger(name);
    }
  }, [setValue, trigger]);

  const getControlValue = (name: Path<T>): PathValue<T, Path<T>> => {
    return getValues()[name];
  };

  const hasFieldError = (name: Path<T>): boolean => !!errors[name];
  const getErrorText = (name: keyof T): string => {
    const error = errors[name]?.message;
    return errorFormatter ? errorFormatter(error as string) : error as string;
  }
  const getFieldError = (name: Path<T>): string | null => {
    return hasFieldError(name) ? getErrorText(name) : null;
  };

  const handleFormSubmit = handleSubmit((data: T) => saveAction(data));

  const registerControl: RegisterControl<T> = (name: Path<T>): RegisterControlReturn<T> => {
    const registerProps = {
      ...register(name),
      onChange: (
        event: React.ChangeEvent<HTMLInputElement>,
      ): void => {
        setControlValue(name, event.target.value as PathValue<T, Path<T>>);
      },
      error: getErrorText(name),
    };
    const field = fields?.find(f => f.name === name);
    if (field?.required) {
      registerProps['required'] = true;
    }
    return registerProps;
  };

  const registerFormButtons = () => {
    return {
      isDirty,
      isValid,
      isEdit,
      handleReset,
    };
  };

  const getFieldChanged = (name: Path<T>): boolean => {
    return getFieldState(name).isDirty;
  };

  const setValidationErrors = (errors: Record<string, string>) => {
    Object.entries(errors).forEach(([name, error]) => {
      setError(name as unknown as Path<T>, { message: error, type: "value" });
    });
  };

  const renderField = (name: Path<T>, context?: unknown): React.ReactNode | null => {
    const field = fields?.find(f => f.name === name);
    if (!field) {
      return null;
    }
    const renderFn = field?.render ?? defaultRender?.bind(this, field.name, field.title);
    if (!renderFn) {
      return null;
    }
    const renderContext: RenderingContext<T> = {
      helpers: {
        registerControl,
        getFieldError,
        setControlValue,
        control,
        getControlValue,
        getFieldChanged,
        hasFieldError,
        trigger,
      },
      title: field.title,
      userContext: context,
    };
    return renderFn(renderContext);
  };

  return {
    handleFormSubmit,
    register,
    registerControl,
    control,
    errors,
    isDirty,
    isValid,
    handleReset,
    setControlValue,
    getControlValue,
    hasFieldError,
    getFieldError,
    registerFormButtons,
    getFieldChanged,
    setValidationErrors,
    renderField,
    trigger,
  };
};
