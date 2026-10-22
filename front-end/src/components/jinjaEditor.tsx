import { FC, useMemo } from "react";
import EditorView, { minimalSetup } from '@uiw/react-codemirror';
import { langs } from '@uiw/codemirror-extensions-langs';
import { autocompletion } from "@codemirror/autocomplete";
import { Input } from "@mantine/core";
import { createJinja2Autocomplete, jinja2Autocomplete, TemplateVariables } from "../utils";

type ComponentProps = {
  value: string;
  onChange: (value: string) => void;
  // Autocompletion variables; the message template variables when omitted
  variables?: TemplateVariables;
  label?: string;
  description?: string;
  error?: string;
  minHeight?: string;
};

export const JinjaEditor: FC<ComponentProps> = ({ value, onChange, variables, label, description, error, minHeight }) => {
  const extensions = useMemo(
    () => [
      minimalSetup(),
      langs.jinja2(),
      autocompletion({
        override: [variables ? createJinja2Autocomplete(variables) : jinja2Autocomplete],
      }),
    ],
    [variables]
  );

  return (
    <Input.Wrapper label={label} description={description} error={error}>
      <EditorView
        className={error ? "cm-error" : undefined}
        theme={"dark"}
        value={value}
        onChange={onChange}
        minHeight={minHeight}
        spellCheck={true}
        extensions={extensions}
      />
    </Input.Wrapper>
  );
};
