import { useEffect, useId, useMemo, useState } from "react";
import CreatableSelect from "react-select/creatable";

const MAX_LANGUAGE_LENGTH = 64;
export const MAX_LANGUAGES = 10;
const MAX_RESULTS = 100;
const suggestedNames = ["English", "Danish", "Spanish", "French", "German", "Arabic", "Chinese", "Hindi"];
const suggestions = suggestedNames.map((label) => ({ value: label, label }));
let languageOptionsPromise;

function loadLanguageOptions() {
  languageOptionsPromise ||= import("../data/languages.json").then(({ default: names }) =>
    names.map((label) => ({ value: label, label })));
  return languageOptionsPromise;
}

export default function LanguageSelect({ value, onChange, id }) {
  const generatedId = useId();
  const inputId = id || generatedId;
  const [inputValue, setInputValue] = useState("");
  const [options, setOptions] = useState(suggestions);
  const selectedLanguages = Array.isArray(value) ? value : [];
  const selectedOption = selectedLanguages.map((label) => ({ value: label, label }));

  useEffect(() => {
    let active = true;
    loadLanguageOptions().then((loaded) => {
      if (active) setOptions(loaded);
    });
    return () => { active = false; };
  }, []);

  const visibleOptions = useMemo(() => {
    const query = inputValue.trim().toLocaleLowerCase();
    if (!query) return suggestions;
    return options.filter((option) => option.label.toLocaleLowerCase().includes(query)).slice(0, MAX_RESULTS);
  }, [inputValue, options]);

  return (
    <CreatableSelect
      inputId={inputId}
      name={`language-${inputId}`}
      options={visibleOptions}
      value={selectedOption}
      inputValue={inputValue}
      onInputChange={(nextValue) => setInputValue(nextValue)}
      onChange={(selected) => onChange((selected || []).map((option) => option.value.trim().replace(/\s+/g, " ")))}
      placeholder="Select or type languages..."
      isSearchable
      isMulti
      isClearable={false}
      isOptionDisabled={() => selectedLanguages.length >= MAX_LANGUAGES}
      isValidNewOption={(candidate) => {
        const name = candidate.trim().replace(/\s+/g, " ");
        return Boolean(name) && name.length <= MAX_LANGUAGE_LENGTH
          && selectedLanguages.length < MAX_LANGUAGES
          && !options.some((option) => option.label.toLocaleLowerCase() === name.toLocaleLowerCase())
          && !selectedLanguages.some((language) => language.toLocaleLowerCase() === name.toLocaleLowerCase());
      }}
      formatCreateLabel={(candidate) => `Add "${candidate.trim()}"`}
      filterOption={null}
      menuPlacement="auto"
      classNamePrefix="form-select"
    />
  );
}
