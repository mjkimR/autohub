// Copied from app-common bf441d0 packages/ui/app-ui-api-codegen; owned and customized by this project.
import ts from 'typescript';
export function memberName(member) {
	if (!member.name || (!ts.isIdentifier(member.name) && !ts.isStringLiteral(member.name))) {
		throw new Error('Unsupported OpenAPI declaration member');
	}
	return member.name.text;
}
export function withMembers(node, members) {
	return ts.isInterfaceDeclaration(node)
		? ts.factory.updateInterfaceDeclaration(
				node,
				node.modifiers,
				node.name,
				node.typeParameters,
				node.heritageClauses,
				members
			)
		: ts.factory.updateTypeLiteralNode(node, ts.factory.createNodeArray(members));
}
export function schemaMembers(components) {
	const schemas = components.members.find((member) => memberName(member) === 'schemas');
	return schemas?.type && ts.isTypeLiteralNode(schemas.type) ? schemas.type.members : [];
}
export function componentNode(original, schemas) {
	return withMembers(
		original,
		original.members.map((member) => {
			if (memberName(member) !== 'schemas') return member;
			const property = member;
			return ts.factory.updatePropertySignature(
				property,
				property.modifiers,
				property.name,
				property.questionToken,
				ts.factory.createTypeLiteralNode(schemas)
			);
		})
	);
}
export function declaration(ast, name) {
	const node = ast.find(
		(node) =>
			(ts.isInterfaceDeclaration(node) || ts.isTypeAliasDeclaration(node)) &&
			node.name.text === name
	);
	if (!node) throw new Error(`Missing OpenAPI declaration ${name}`);
	if (ts.isInterfaceDeclaration(node)) return node;
	// openapi-typescript emits never/Record<string, never> aliases for empty sections.
	return ts.factory.createInterfaceDeclaration(
		[ts.factory.createModifier(ts.SyntaxKind.ExportKeyword)],
		name,
		undefined,
		undefined,
		[]
	);
}
