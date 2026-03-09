import { useMemo } from "react";
import Select from "react-select";
import countries from "i18n-iso-countries";
import en from "i18n-iso-countries/langs/en.json";

countries.registerLocale(en);

export default function CountrySelect({
  value,
  onChange,
  name = "country",
  placeholder = "Select a country...",
  isClearable = true,
  isMulti = false,
}) {
  const options = useMemo(() => {
    return Object.entries(countries.getNames("en", { select: "official" }))
      .map(([code, label]) => ({
        value: code,
        label,
      }))
      .sort((a, b) => a.label.localeCompare(b.label));
  }, []);

  const selectedOption = isMulti
    ? options.filter((option) => Array.isArray(value) && value.includes(option.value))
    : options.find((option) => option.value === value) || null;

  function handleChange(selected) {
    if (isMulti) {
      onChange(selected ? selected.map((option) => option.value) : []);
      return;
    }

    onChange(selected ? selected.value : "");
  }

  return (
    <Select
      inputId={name}
      name={name}
      options={options}
      value={selectedOption}
      onChange={handleChange}
      placeholder={placeholder}
      isClearable={isClearable}
      isSearchable
      isMulti={isMulti}
      classNamePrefix="form-select"
    />
  );
}