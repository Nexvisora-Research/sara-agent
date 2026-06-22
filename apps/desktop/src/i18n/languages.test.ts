import { describe, expect, it } from 'vitest'

import { DEFAULT_LOCALE, isLocale, isSupportedLocaleValue, localeConfigValue, normalizeLocale } from './languages'

describe('desktop i18n languages', () => {
  it('normalizes supported locale aliases', () => {
    expect(normalizeLocale('en')).toBe('en')
    expect(normalizeLocale('EN-US')).toBe('en')
    expect(normalizeLocale('zh')).toBe('zh')
    expect(normalizeLocale('zh-CN')).toBe('zh')
    expect(normalizeLocale('zh-Hans')).toBe('zh')
    expect(normalizeLocale(' zh_hans_cn ')).toBe('zh')
    expect(normalizeLocale('zh-Hant')).toBe('zh-hant')
    expect(normalizeLocale('zh-TW')).toBe('zh-hant')
    expect(normalizeLocale('zh_HK')).toBe('zh-hant')
    expect(normalizeLocale('ja')).toBe('ja')
    expect(normalizeLocale('ja-JP')).toBe('ja')
  })

  it('falls back to English for empty or unsupported values', () => {
    expect(normalizeLocale(null)).toBe(DEFAULT_LOCALE)
    expect(normalizeLocale('')).toBe(DEFAULT_LOCALE)
    expect(normalizeLocale('xx')).toBe(DEFAULT_LOCALE)
  })

  it('normalizes new locale aliases', () => {
    expect(normalizeLocale('ko')).toBe('ko')
    expect(normalizeLocale('ko-KR')).toBe('ko')
    expect(normalizeLocale('fr')).toBe('fr')
    expect(normalizeLocale('fr-FR')).toBe('fr')
    expect(normalizeLocale('fr-CA')).toBe('fr')
    expect(normalizeLocale('de')).toBe('de')
    expect(normalizeLocale('de-DE')).toBe('de')
    expect(normalizeLocale('de-AT')).toBe('de')
    expect(normalizeLocale('es')).toBe('es')
    expect(normalizeLocale('es-ES')).toBe('es')
    expect(normalizeLocale('es-MX')).toBe('es')
  })

  it('distinguishes exact locale ids from supported config aliases', () => {
    expect(isSupportedLocaleValue('zh-CN')).toBe(true)
    expect(isSupportedLocaleValue('zh-TW')).toBe(true)
    expect(isSupportedLocaleValue('ja-JP')).toBe(true)
    expect(isSupportedLocaleValue('ko-KR')).toBe(true)
    expect(isSupportedLocaleValue('fr-FR')).toBe(true)
    expect(isSupportedLocaleValue('de-DE')).toBe(true)
    expect(isSupportedLocaleValue('es-ES')).toBe(true)
    expect(isLocale('zh-CN')).toBe(false)
    expect(isLocale('zh')).toBe(true)
    expect(isLocale('zh-hant')).toBe(true)
    expect(isLocale('ja')).toBe(true)
    expect(isLocale('ko')).toBe(true)
    expect(isLocale('fr')).toBe(true)
    expect(isLocale('de')).toBe(true)
    expect(isLocale('es')).toBe(true)
  })

  it('returns the persisted config value for supported locales', () => {
    expect(localeConfigValue('en')).toBe('en')
    expect(localeConfigValue('zh')).toBe('zh')
    expect(localeConfigValue('zh-hant')).toBe('zh-hant')
    expect(localeConfigValue('ja')).toBe('ja')
    expect(localeConfigValue('ko')).toBe('ko')
    expect(localeConfigValue('fr')).toBe('fr')
    expect(localeConfigValue('de')).toBe('de')
    expect(localeConfigValue('es')).toBe('es')
  })
})
