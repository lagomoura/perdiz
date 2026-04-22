/**
 * Registry for customization type renderers.
 * To add a new customization type (see docs/product/customization-model.md):
 *   1. Add the enum value in the backend.
 *   2. Implement a renderer component.
 *   3. Register it here.
 */
import type { ComponentType } from 'react';

export type CustomizationType =
  | 'COLOR'
  | 'MATERIAL'
  | 'SIZE'
  | 'ENGRAVING_TEXT'
  | 'ENGRAVING_IMAGE'
  | 'USER_FILE';

export type CustomizationGroupProps = {
  groupId: string;
  // full typing lands with the feature implementation
};

export const customizationRenderers: Record<
  CustomizationType,
  ComponentType<CustomizationGroupProps> | null
> = {
  COLOR: null,
  MATERIAL: null,
  SIZE: null,
  ENGRAVING_TEXT: null,
  ENGRAVING_IMAGE: null,
  USER_FILE: null,
};
