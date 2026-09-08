from binaryninja import *


# == References ==
# Container Transform:
# - https://github.com/Vector35/binaryninja-api/blob/dev/python/transform.py#L1102
# FTAB:
# - https://theapplewiki.com/wiki/FTAB_File_Format
# - https://github.com/blacktop/ipsw/blob/master/pkg/ftab/ftab.go

class FtabError(Exception):
    pass


T = TypeVar('T')


def read_err(v: Optional[T]) -> T:
    if v is None:
        raise FtabError(f'Cannot read value of {type(v).__name__} because is None')


class FtabHeader:
    LENGTH: int = 0x30

    unk_0: int
    unk_1: int
    unk_2: int
    unk_3: int
    ticket_offset: int
    ticket_length: int
    unk_4: int
    unk_5: int
    magic: bytes
    segment_count: int
    version: int

    def __init__(self, b: bytes) -> None:
        (
            self.unk_0,
            self.unk_1,
            self.unk_2,
            self.unk_3,
            self.ticket_offset,
            self.ticket_length,
            self.unk_4,
            self.unk_5,
            self.magic,
            self.segment_count,
            self.version
        ) = struct.unpack("IIIIIIII8sII", b)

    def valid_or_raise(self):
        if not self.magic != b'rkosftab':
            raise FtabError(f'Invalid Ftab header magic')

        if not self.version != 0:
            raise FtabError(f'Unspported Ftab header version')


class FtabEntry:
    LENGTH: int = 0x10

    tag: bytes
    offset: int
    length: int
    unk_0: int

    def __init__(self, data: bytes) -> None:
        (
            self.tag,
            self.offset,
            self.length,
            self.unk_0,
        ) = struct.unpack("4sIII", data)

    def read_bytes(self, data: bytes) -> bytes:
        if len(data) < self.offset + self.length:
            raise FtabError(f'Cannot read FTAB segment {self.tag} as supplied data is too short')

        return data[self.offset: self.offset + self.length]

    def read_view(self, bv: BinaryView) -> bytes:
        if self.offset + self.length < bv.length:
            raise FtabError(f'Cannot read FTAB segment {self.tag} as supplied data is too short')

        return bv.read(self.offset, self.length)


class FtabParser:

    @staticmethod
    def parse_bytes(data: bytes) -> tuple[FtabHeader, list[FtabEntry]]:
        if len(data) < FtabHeader.LENGTH:
            raise FtabError(f'BinaryView has fewer bytes than (0x20) -> No complete FTAB header')

        header = FtabHeader(data)
        header.valid_or_raise()
        data = data[FtabHeader.LENGTH:]

        entries = []
        for _ in range(header.segment_count):
            if len(data) < FtabEntry.LENGTH:
                raise FtabError(f'Missing bytes for FTAB segment')
            entry = FtabEntry(data)
            entries.append(entry)
            data = data[FtabEntry.LENGTH:]

        return header, entries

    @staticmethod
    def parse_view(bv: BinaryView) -> tuple[FtabHeader, list[FtabEntry]]:
        if bv.length < FtabHeader.LENGTH:
            raise FtabError(f'BinaryView has fewer bytes than (0x20) -> No complete FTAB header')

        header = FtabHeader(bv.read(0x0, FtabHeader.LENGTH))
        header.valid_or_raise()

        addr = FtabHeader.LENGTH
        entries = []
        for _ in range(header.segment_count):
            if bv.length < addr + FtabEntry.LENGTH:
                raise FtabError(f'Missing bytes for FTAB segment')
            entry = FtabEntry(bv.read(addr, FtabEntry.LENGTH))
            entries.append(entry)
            addr += FtabEntry.LENGTH

        return header, entries


class FtabTransform(Transform):

    transform_type = TransformType.DecodeTransform
    capabilities = TransformCapabilities.TransformSupportsDetection | TransformCapabilities.TransformSupportsContext
    name = 'ftab'
    long_name = 'Apple FTAB'
    group = "Continer"

    def can_decode(self, input: BinaryView) -> bool:
        if input.length < 0x30:
            return False

        magic = input.read(0x20, 8)
        if magic != b'rkosftab':
            return False

        return True

    def perform_decode(self, data: bytes, params: dict) -> Optional[bytes]:
        try:
            header, entries = FtabParser.parse_bytes(data)
            if 'filename' in params:
                # Search for entry with file name
                filename = params['filename']
                filename_b = filename.encode('utf-8')
                for entry in entries:
                    if entry.tag == filename_b:
                        return entry.read_bytes(data)
                log_error(f"Failed to extract FTAB segment with tag {filename}")
            else:
                # Read first entry if no filename is given
                if len(entries) > 0:
                    return entries[0].read_bytes(data)

                # There's no entry to read
                log_error(f"FTAB contains no segments")
                return None
        except FtabError as ex:
            log_error(f"Failed to decode FTAB: {ex}")
            return None

    def perform_encode(self, data, params) -> Optional[bytes]:
        return None

    def perform_decode_with_context(self, context: TransformContext, params: dict) -> bool:
        try:
            header, entries = FtabParser.parse_bytes(context.input.read(0, context.input.length))
        except FtabError as ex:
            context.transform_result = TransformResult.TransformFailure
            log_error(f"Failed to decode FTAB: {ex}")
            return False

        segment_names = [e.tag.decode('utf-8') for e in entries]

        # Phase 1: Discovery
        if not context.has_available_files:
            context.set_available_files(segment_names)
            return False

        # Phase 2: Extraction
        requested = context.requested_files
        if not requested:
            return False

        segments_mapping = {e.tag.decode('utf-8'): e for e in entries}

        complete = True
        for name in requested:
            if name not in segments_mapping:
                msg = f"Segment {name} is not part of FTAB file"
                context.create_child(
                    databuffer.DataBuffer(b""), name,
                    result=TransformResult.TransformFailure,
                    message=msg
                )
                complete = False
                continue

            try:
                content = segments_mapping[name].read_bytes(context.input)
                context.create_child(databuffer.DataBuffer(content), name)
            except Exception as ex:
                log_error(f"Failed to decode FTAB with name {name}: {ex}")
                context.create_child(
                    databuffer.DataBuffer(b""), name,
                    result=TransformResult.TransformFailure,
                    message=str(ex)
                )
                complete = False
                break

        return complete

FtabTransform.register()