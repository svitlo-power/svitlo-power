
import React from 'react';
import { AVAILABLE_LANGUAGES } from '../i18n';
import type { LocalizableValue } from '../schemas/base';
import { Stack, TextInput } from '@mantine/core';
import { CountryFlag } from './countryFlag';
import { TFunction } from 'i18next';

type Props = {
	t: TFunction,
	value?: Partial<LocalizableValue>;
	onChange?: (v: LocalizableValue) => void;
	className?: string;
	label: string;
	valueErrors?: Record<string, string>;
};

export const LocalizableValueEditor: React.FC<Props> = ({ t, value = {}, onChange, className, label, valueErrors = {} }) => {
	const handleChange = (lang: string, text: string) => {
		const next: LocalizableValue = { ...value, [lang]: text } as LocalizableValue;
		onChange?.(next);
	};

	return (
		<Stack gap="xs" className={className}>
			{AVAILABLE_LANGUAGES.map((lang) => (
				<div key={lang}>
					<TextInput
						label={`${label} (${t(`lang.${lang}`)})`}
						value={value[lang] ?? ''}
						onChange={(e) => handleChange(lang, e.target.value)}
						error={valueErrors?.[lang]}
						leftSection={<CountryFlag language={lang}/>}
					/>
				</div>
			))}
		</Stack>
	);
};
