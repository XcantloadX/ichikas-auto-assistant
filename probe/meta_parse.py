"""最小 il2cpp global-metadata.dat 解析器（v31 / Unity 2022.3 足够用）"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field


@dataclass
class Metadata:
    path: str
    data: bytes
    version: int
    string_offset: int
    string_size: int
    type_defs_offset: int
    type_defs_size: int
    fields_offset: int
    fields_size: int
    images_offset: int
    images_size: int

    # ---- header 字段名（v24.1+ 顺序）----
    HEADER_FIELDS = [
        'sanity', 'version',
        'stringLiteralOffset', 'stringLiteralCount',
        'stringLiteralDataOffset', 'stringLiteralDataCount',
        'stringOffset', 'stringCount',
        'eventsOffset', 'eventsCount',
        'propertiesOffset', 'propertiesCount',
        'methodsOffset', 'methodsCount',
        'parameterDefaultValuesOffset', 'parameterDefaultValuesCount',
        'fieldDefaultValuesOffset', 'fieldDefaultValuesCount',
        'fieldAndParameterDefaultValueDataOffset', 'fieldAndParameterDefaultValueDataCount',
        'fieldMarshaledSizesOffset', 'fieldMarshaledSizesCount',
        'parametersOffset', 'parametersCount',
        'genericParametersOffset', 'genericParametersCount',
        'genericParameterConstraintsOffset', 'genericParameterConstraintsCount',
        'genericContainersOffset', 'genericContainersCount',
        'nestedTypesOffset', 'nestedTypesCount',
        'interfacesOffset', 'interfacesCount',
        'vtableMethodsOffset', 'vtableMethodsCount',
        'interfaceImplsOffset', 'interfaceImplsCount',
        'typeDefinitionsOffset', 'typeDefinitionsCount',
        'imagesOffset', 'imagesCount',
        'assembliesOffset', 'assembliesCount',
        'fieldRefsOffset', 'fieldRefsCount',
        'referencedAssembliesOffset', 'referencedAssembliesCount',
        'attributeDataOffset', 'attributeDataCount',
        'attributeDataRangeOffset', 'attributeDataRangeCount',
        'unresolvedIndirectCallParameterTypesOffset', 'unresolvedIndirectCallParameterTypesCount',
        'unresolvedIndirectCallParameterRangesOffset', 'unresolvedIndirectCallParameterRangesCount',
        'windowsRuntimeTypeNamesOffset', 'windowsRuntimeTypeNamesSize',
        'windowsRuntimeStringsOffset', 'windowsRuntimeStringsSize',
        'exportedTypeDefinitionsOffset', 'exportedTypeDefinitionsCount',
    ]

    @classmethod
    def load(cls, path: str) -> 'Metadata':
        data = open(path, 'rb').read()
        sanity, version = struct.unpack_from('<II', data, 0)
        assert sanity == 0xFAB11BAF, f'bad metadata sanity {sanity:#x}'
        # 逐对读 header
        vals = {}
        for i, name in enumerate(cls.HEADER_FIELDS[2:]):
            off = 8 + i * 4
            if off + 4 > len(data):
                break
            vals[name] = struct.unpack_from('<I', data, off)[0]
        # v24.1+ TypeDefinition 大小 0x5C；v27(24.4)+ 也 0x5C；v29 0x60? 用 0x5C 试探
        return cls(
            path=path, data=data, version=version,
            string_offset=vals['stringOffset'], string_size=vals['stringCount'],
            type_defs_offset=vals['typeDefinitionsOffset'], type_defs_size=vals['typeDefinitionsCount'],
            fields_offset=vals['fieldsOffset'], fields_size=vals['fieldsCount'],
            images_offset=vals['imagesOffset'], images_size=vals['imagesCount'],
        )

    def get_string(self, index: int) -> str:
        start = self.string_offset + index
        end = self.data.index(b'\x00', start)
        return self.data[start:end].decode('utf-8', 'replace')

    def type_def_struct_size(self) -> int:
        # 探测: typeDefinitionsCount * size ≈ 与 imagesOffset 相邻关系
        return 0x5C

    def iter_type_defs(self):
        size = self.type_def_struct_size()
        for i in range(self.type_defs_size):
            off = self.type_defs_offset + i * size
            (name_idx, ns_idx, byval, byref, declaring, parent, elem,
             generic_container, flags, field_start, method_start, event_start,
             property_start, nested_start, iface_start, vtable_start, iface_off_start,
             method_count, prop_count, field_count, event_count, nested_count,
             vtable_count, iface_count, iface_off_count, bitfield, token) = struct.unpack_from(
                '<i i i i i i i i I i i i i i i i i H H H H H H H H I I i', self.data, off)
            yield {
                'index': i, 'name_index': name_idx, 'ns_index': ns_idx,
                'flags': flags, 'field_start': field_start, 'field_count': field_count,
                'method_start': method_start, 'method_count': method_count,
                'name': self.get_string(name_idx), 'ns': self.get_string(ns_idx),
            }

    def find_type(self, ns: str, name: str) -> dict | None:
        for td in self.iter_type_defs():
            if td['name'] == name and td['ns'] == ns:
                return td
        return None

    def get_fields(self, td: dict) -> list[dict]:
        out = []
        for i in range(td['field_start'], td['field_start'] + td['field_count']):
            off = self.fields_offset + i * 12  # Il2CppFieldDefinition: nameIndex, typeIndex, token
            name_idx, type_idx, token = struct.unpack_from('<i I I', self.data, off)
            out.append({'name': self.get_string(name_idx), 'type_index': type_idx, 'token': token})
        return out


if __name__ == '__main__':
    m = Metadata.load('global-metadata.dat')
    print('version:', m.version)
    print('string region:', hex(m.string_offset), m.string_size)
    td = m.find_type('UnityEngine', 'GameObject')
    print('GameObject typeDef:', {k: v for k, v in td.items() if k not in ('name', 'ns')} if td else None)
    if td:
        for f in m.get_fields(td):
            print('  field:', f['name'])
